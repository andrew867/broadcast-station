import numpy as np
import cv2


def ecef(lat, lon, height):
    """WGS84 geodetic degrees and ellipsoidal metres to ECEF metres."""
    lat, lon = np.radians([lat, lon])
    a, e2 = 6378137.0, 6.6943799901413165e-3
    n = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)
    return np.array([(n + height) * np.cos(lat) * np.cos(lon),
                     (n + height) * np.cos(lat) * np.sin(lon),
                     (n * (1 - e2) + height) * np.sin(lat)])


def enu_rotation(lat, lon):
    p, l = np.radians([lat, lon])
    return np.array([[-np.sin(l), np.cos(l), 0],
                     [-np.sin(p)*np.cos(l), -np.sin(p)*np.sin(l), np.cos(p)],
                     [np.cos(p)*np.cos(l), np.cos(p)*np.sin(l), np.sin(p)]])


def site_frame(site):
    # h = H + N. A missing N is allowed only for a provisional solve.
    h = site.altitude_msl_m + (site.geoid_separation_m or 0)
    return ecef(site.lat, site.lon, h), enu_rotation(site.lat, site.lon)


def project(points, calibration):
    points = np.asarray(points, dtype=float).reshape(-1, 3)
    r = np.asarray(calibration['rvec'], float)
    rot = cv2.Rodrigues(r)[0]
    depth = (points @ rot.T)[:, 2]
    pixels = cv2.projectPoints(points, r, np.zeros(3),
                              np.array(calibration['K']),
                              np.array(calibration['distortion']))[0].reshape(-1, 2)
    return pixels, depth
