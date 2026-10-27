"""Constrained fixed-origin calibration. No guessed landmark coordinates."""
import cv2
import numpy as np
from scipy.optimize import least_squares
from .geometry import ecef, site_frame, project


def solve(request):
    pts = request.landmarks
    train = np.array([not p.validation for p in pts])
    minimum = 10 if request.fit_distortion else 6
    if train.sum() < minimum:
        raise ValueError(f'Need at least {minimum} fitting landmarks; add 3 separate validation landmarks for approval')
    origin, basis = site_frame(request.site)
    world = np.array([basis @ (ecef(p.lat, p.lon, p.altitude_msl_m +
                      (p.geoid_separation_m if p.geoid_separation_m is not None else
                       request.site.geoid_separation_m or 0)) - origin) for p in pts])
    image = np.array([[p.x, p.y] for p in pts], dtype=float)
    if np.any(np.linalg.norm(world, axis=1) < 10):
        raise ValueError('Landmarks must be at least 10 metres from the camera')
    span = np.ptp(image[train], axis=0) / [request.width, request.height]
    if span[0] < .35 or span[1] < .08:
        raise ValueError('Landmarks need wider horizontal and vertical coverage; a thin skyline cannot constrain this solve')
    if len(np.unique(image[train], axis=0)) != train.sum():
        raise ValueError('Duplicate fitting pixel coordinates')
    width, height = request.width, request.height
    def matrix(f):
        return np.array([[f, 0, width/2], [0, f, height/2], [0, 0, 1.]])
    def unpack(v):
        d = np.array([v[4], v[5], 0., 0., 0.]) if request.fit_distortion else np.zeros(5)
        return matrix(np.exp(v[3])), d
    def residual(v, mask=train):
        k, d = unpack(v)
        pred = cv2.projectPoints(world[mask], v[:3], np.zeros(3), k, d)[0].reshape(-1, 2)
        return (pred - image[mask]).ravel()
    candidates = []
    lower = [-np.inf]*3 + [np.log(width/2/np.tan(np.radians(150/2)))]
    upper = [np.inf]*3 + [np.log(width/2/np.tan(np.radians(20/2)))]
    if request.fit_distortion:
        lower += [-.7, -.4]
        upper += [.7, .4]
    # solvePnP supplies orientation seeds; translation is deliberately fixed at
    # the surveyed origin during final robust optimization, avoiding skyline drift.
    for hfov in sorted(set([35, 60, 90, 120, request.initial_hfov_deg])):
        f = width/2 / np.tan(np.radians(hfov/2))
        k = matrix(f)
        try:
            ok, r, _, inliers = cv2.solvePnPRansac(world[train], image[train], k, np.zeros(5),
                flags=cv2.SOLVEPNP_EPNP, reprojectionError=12, iterationsCount=300)
            if not ok:
                ok, r, _ = cv2.solvePnP(world[train], image[train], k, np.zeros(5), flags=cv2.SOLVEPNP_EPNP)
            if not ok:
                continue
            initial = list(r.ravel()) + [np.log(f)] + ([0., 0.] if request.fit_distortion else [])
            fit = least_squares(residual, initial, bounds=(lower, upper), loss='soft_l1',
                                f_scale=2, max_nfev=1500, x_scale='jac')
            depth = (world @ cv2.Rodrigues(fit.x[:3])[0].T)[:, 2]
            if np.all(depth > 0) and fit.success:
                candidates.append(fit)
        except cv2.error:
            continue
    if not candidates:
        raise ValueError('No physically valid solution. Check landmark coordinates and field of view')
    fit = min(candidates, key=lambda f: f.cost)
    k, d = unpack(fit.x)
    forward = cv2.Rodrigues(fit.x[:3])[0][2]
    result = {'rvec': fit.x[:3].tolist(), 'K': k.tolist(), 'distortion': d.tolist(),
              'bearing_deg': float(np.degrees(np.arctan2(forward[0],forward[1])) % 360),
              'elevation_deg': float(np.degrees(np.arcsin(np.clip(forward[2],-1,1)))),
              'hfov_deg': float(np.degrees(2*np.arctan(width/(2*k[0,0])))),
              'vfov_deg': float(np.degrees(2*np.arctan(height/(2*k[1,1])))),
              'origin_policy': 'fixed at supplied site; principal point centered; square pixels',
              'model': 'pinhole with radial k1,k2; tangential and k3 fixed to zero'}
    predicted, _ = project(world, result)
    errors = np.linalg.norm(predicted-image, axis=1)
    inliers = train & (errors <= 5)
    rms = lambda mask: float(np.sqrt(np.mean(errors[mask]**2))) if mask.any() else None
    warnings = []
    if not request.site.verified:
        warnings.append('Camera location and elevation remain provisional')
    if request.site.geoid_separation_m is None:
        warnings.append('AMSL to WGS84 geoid separation is missing')
    if (~train).sum() < 3:
        warnings.append('Need at least 3 independent validation landmarks')
    elif rms(~train) > 5:
        warnings.append('Validation RMS exceeds 5 pixels')
    if inliers.sum() < minimum or rms(train) > 5:
        warnings.append('Fitting residuals exceed acceptance limits; inspect outliers')
    if request.fit_distortion and (span[0] < .65 or span[1] < .3):
        warnings.append('Radial distortion needs landmarks across at least 65% width and 30% height')
    # Inspect radial mapping across the full raster, including corners.
    rr = np.linspace(0, (width/2/k[0,0])**2 + (height/2/k[1,1])**2, 100)
    if np.any(1+3*d[0]*rr+5*d[1]*rr**2 <= .1):
        warnings.append('Distortion folds or compresses the image near its edges')
    if np.any(fit.active_mask):
        warnings.append('A fitted parameter reached its bound')
    singular = np.linalg.svd(fit.jac / np.maximum(np.linalg.norm(fit.jac, axis=0), 1e-12), compute_uv=False)
    condition = float(singular[0]/max(singular[-1], 1e-15))
    if condition > 1e5:
        warnings.append('Calibration geometry is poorly constrained')
    result.update(rms_px=rms(train), validation_rms_px=rms(~train), max_error_px=float(errors.max()),
                  inlier_count=int(inliers.sum()), condition_number=condition, warnings=warnings,
                  acceptable=not warnings,
                  points=[{'name': p.name, 'observed': [p.x,p.y], 'projected': q.tolist(),
                           'error_px': float(e), 'validation': p.validation, 'inlier': bool(e<=5)}
                          for p,q,e in zip(pts,predicted,errors)])
    return result
