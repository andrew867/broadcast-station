var __defProp = Object.defineProperty;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __esm = (fn2, res) => function __init() {
  return fn2 && (res = (0, fn2[__getOwnPropNames(fn2)[0]])(fn2 = 0)), res;
};
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};

// outputs/skycam/labs/strudel/node_modules/fraction.js/dist/fraction.mjs
function assign(n, s) {
  try {
    n = BigInt(n);
  } catch (e) {
    throw InvalidParameter();
  }
  return n * s;
}
function ifloor(x) {
  return typeof x === "bigint" ? x : Math.floor(x);
}
function newFraction(n, d2) {
  if (d2 === C_ZERO) {
    throw DivisionByZero();
  }
  const f2 = Object.create(Fraction.prototype);
  f2["s"] = n < C_ZERO ? -C_ONE : C_ONE;
  n = n < C_ZERO ? -n : n;
  const a = gcd(n, d2);
  f2["n"] = n / a;
  f2["d"] = d2 / a;
  return f2;
}
function factorize(n) {
  const factors = /* @__PURE__ */ Object.create(null);
  if (n <= C_ONE) {
    factors[n] = C_ONE;
    return factors;
  }
  const add2 = (p) => {
    factors[p] = (factors[p] || C_ZERO) + C_ONE;
  };
  while (n % C_TWO === C_ZERO) {
    add2(C_TWO);
    n /= C_TWO;
  }
  while (n % C_THREE === C_ZERO) {
    add2(C_THREE);
    n /= C_THREE;
  }
  while (n % C_FIVE === C_ZERO) {
    add2(C_FIVE);
    n /= C_FIVE;
  }
  for (let si2 = 0, p = C_TWO + C_FIVE; p * p <= n; ) {
    while (n % p === C_ZERO) {
      add2(p);
      n /= p;
    }
    p += FACTORSTEPS[si2];
    si2 = si2 + 1 & 7;
  }
  if (n > C_ONE) add2(n);
  return factors;
}
function modpow(b, e, m2) {
  let r = C_ONE;
  for (; e > C_ZERO; b = b * b % m2, e >>= C_ONE) {
    if (e & C_ONE) {
      r = r * b % m2;
    }
  }
  return r;
}
function cycleLen(n, d2) {
  for (; d2 % C_TWO === C_ZERO; d2 /= C_TWO) {
  }
  for (; d2 % C_FIVE === C_ZERO; d2 /= C_FIVE) {
  }
  if (d2 === C_ONE)
    return C_ZERO;
  let rem = C_TEN % d2;
  let t = 1;
  for (; rem !== C_ONE; t++) {
    rem = rem * C_TEN % d2;
    if (t > MAX_CYCLE_LEN)
      return C_ZERO;
  }
  return BigInt(t);
}
function cycleStart(n, d2, len) {
  let rem1 = C_ONE;
  let rem2 = modpow(C_TEN, len, d2);
  for (let t = 0; t < 300; t++) {
    if (rem1 === rem2)
      return BigInt(t);
    rem1 = rem1 * C_TEN % d2;
    rem2 = rem2 * C_TEN % d2;
  }
  return 0;
}
function gcd(a, b) {
  if (!a)
    return b;
  if (!b)
    return a;
  while (1) {
    a %= b;
    if (!a)
      return b;
    b %= a;
    if (!b)
      return a;
  }
}
function Fraction(a, b) {
  parse(a, b);
  if (this instanceof Fraction) {
    a = gcd(P["d"], P["n"]);
    this["s"] = P["s"];
    this["n"] = P["n"] / a;
    this["d"] = P["d"] / a;
  } else {
    return newFraction(P["s"] * P["n"], P["d"]);
  }
}
var C_ZERO, C_ONE, C_TWO, C_THREE, C_FIVE, C_TEN, MAX_INTEGER, MAX_CYCLE_LEN, P, FACTORSTEPS, parse, DivisionByZero, InvalidParameter, NonIntegerParameter;
var init_fraction = __esm({
  "outputs/skycam/labs/strudel/node_modules/fraction.js/dist/fraction.mjs"() {
    "use strict";
    if (typeof BigInt === "undefined") BigInt = function(n) {
      if (isNaN(n)) throw new Error("");
      return n;
    };
    C_ZERO = BigInt(0);
    C_ONE = BigInt(1);
    C_TWO = BigInt(2);
    C_THREE = BigInt(3);
    C_FIVE = BigInt(5);
    C_TEN = BigInt(10);
    MAX_INTEGER = BigInt(Number.MAX_SAFE_INTEGER);
    MAX_CYCLE_LEN = 2e3;
    P = {
      "s": C_ONE,
      "n": C_ZERO,
      "d": C_ONE
    };
    FACTORSTEPS = [C_TWO * C_TWO, C_TWO, C_TWO * C_TWO, C_TWO, C_TWO * C_TWO, C_TWO * C_THREE, C_TWO, C_TWO * C_THREE];
    parse = function(p1, p2) {
      let n = C_ZERO, d2 = C_ONE, s = C_ONE;
      if (p1 === void 0 || p1 === null) {
      } else if (p2 !== void 0) {
        if (typeof p1 === "bigint") {
          n = p1;
        } else if (isNaN(p1)) {
          throw InvalidParameter();
        } else if (p1 % 1 !== 0) {
          throw NonIntegerParameter();
        } else {
          n = BigInt(p1);
        }
        if (typeof p2 === "bigint") {
          d2 = p2;
        } else if (isNaN(p2)) {
          throw InvalidParameter();
        } else if (p2 % 1 !== 0) {
          throw NonIntegerParameter();
        } else {
          d2 = BigInt(p2);
        }
        s = n * d2;
      } else if (typeof p1 === "object") {
        if ("d" in p1 && "n" in p1) {
          n = BigInt(p1["n"]);
          d2 = BigInt(p1["d"]);
          if ("s" in p1)
            n *= BigInt(p1["s"]);
        } else if (0 in p1) {
          n = BigInt(p1[0]);
          if (1 in p1)
            d2 = BigInt(p1[1]);
        } else if (typeof p1 === "bigint") {
          n = p1;
        } else {
          throw InvalidParameter();
        }
        s = n * d2;
      } else if (typeof p1 === "number") {
        if (isNaN(p1)) {
          throw InvalidParameter();
        }
        if (p1 < 0) {
          s = -C_ONE;
          p1 = -p1;
        }
        if (p1 % 1 === 0) {
          n = BigInt(p1);
        } else {
          let z2 = 1;
          let A = 0, B2 = 1;
          let C2 = 1, D = 1;
          let N2 = 1e7;
          if (p1 >= 1) {
            z2 = 10 ** Math.floor(1 + Math.log10(p1));
            p1 /= z2;
          }
          while (B2 <= N2 && D <= N2) {
            let M = (A + C2) / (B2 + D);
            if (p1 === M) {
              if (B2 + D <= N2) {
                n = A + C2;
                d2 = B2 + D;
              } else if (D > B2) {
                n = C2;
                d2 = D;
              } else {
                n = A;
                d2 = B2;
              }
              break;
            } else {
              if (p1 > M) {
                A += C2;
                B2 += D;
              } else {
                C2 += A;
                D += B2;
              }
              if (B2 > N2) {
                n = C2;
                d2 = D;
              } else {
                n = A;
                d2 = B2;
              }
            }
          }
          n = BigInt(n) * BigInt(z2);
          d2 = BigInt(d2);
        }
      } else if (typeof p1 === "string") {
        let ndx = 0;
        let v = C_ZERO, w2 = C_ZERO, x = C_ZERO, y = C_ONE, z2 = C_ONE;
        let match = p1.replace(/_/g, "").match(/\d+|./g);
        if (match === null)
          throw InvalidParameter();
        if (match[ndx] === "-") {
          s = -C_ONE;
          ndx++;
        } else if (match[ndx] === "+") {
          ndx++;
        }
        if (match.length === ndx + 1) {
          w2 = assign(match[ndx++], s);
        } else if (match[ndx + 1] === "." || match[ndx] === ".") {
          if (match[ndx] !== ".") {
            v = assign(match[ndx++], s);
          }
          ndx++;
          if (ndx + 1 === match.length || match[ndx + 1] === "(" && match[ndx + 3] === ")" || match[ndx + 1] === "'" && match[ndx + 3] === "'") {
            w2 = assign(match[ndx], s);
            y = C_TEN ** BigInt(match[ndx].length);
            ndx++;
          }
          if (match[ndx] === "(" && match[ndx + 2] === ")" || match[ndx] === "'" && match[ndx + 2] === "'") {
            x = assign(match[ndx + 1], s);
            z2 = C_TEN ** BigInt(match[ndx + 1].length) - C_ONE;
            ndx += 3;
          }
        } else if (match[ndx + 1] === "/" || match[ndx + 1] === ":") {
          w2 = assign(match[ndx], s);
          y = assign(match[ndx + 2], C_ONE);
          ndx += 3;
        } else if (match[ndx + 3] === "/" && match[ndx + 1] === " ") {
          v = assign(match[ndx], s);
          w2 = assign(match[ndx + 2], s);
          y = assign(match[ndx + 4], C_ONE);
          ndx += 5;
        }
        if (match.length <= ndx) {
          d2 = y * z2;
          s = /* void */
          n = x + d2 * v + z2 * w2;
        } else {
          throw InvalidParameter();
        }
      } else if (typeof p1 === "bigint") {
        n = p1;
        s = p1;
        d2 = C_ONE;
      } else {
        throw InvalidParameter();
      }
      if (d2 === C_ZERO) {
        throw DivisionByZero();
      }
      P["s"] = s < C_ZERO ? -C_ONE : C_ONE;
      P["n"] = n < C_ZERO ? -n : n;
      P["d"] = d2 < C_ZERO ? -d2 : d2;
    };
    DivisionByZero = function() {
      return new Error("Division by Zero");
    };
    InvalidParameter = function() {
      return new Error("Invalid argument");
    };
    NonIntegerParameter = function() {
      return new Error("Parameters must be integer");
    };
    Fraction.prototype = {
      "s": C_ONE,
      "n": C_ZERO,
      "d": C_ONE,
      /**
       * Calculates the absolute value
       *
       * Ex: new Fraction(-4).abs() => 4
       **/
      "abs": function() {
        return newFraction(this["n"], this["d"]);
      },
      /**
       * Inverts the sign of the current fraction
       *
       * Ex: new Fraction(-4).neg() => 4
       **/
      "neg": function() {
        return newFraction(-this["s"] * this["n"], this["d"]);
      },
      /**
       * Adds two rational numbers
       *
       * Ex: new Fraction({n: 2, d: 3}).add("14.9") => 467 / 30
       **/
      "add": function(a, b) {
        parse(a, b);
        return newFraction(
          this["s"] * this["n"] * P["d"] + P["s"] * this["d"] * P["n"],
          this["d"] * P["d"]
        );
      },
      /**
       * Subtracts two rational numbers
       *
       * Ex: new Fraction({n: 2, d: 3}).add("14.9") => -427 / 30
       **/
      "sub": function(a, b) {
        parse(a, b);
        return newFraction(
          this["s"] * this["n"] * P["d"] - P["s"] * this["d"] * P["n"],
          this["d"] * P["d"]
        );
      },
      /**
       * Multiplies two rational numbers
       *
       * Ex: new Fraction("-17.(345)").mul(3) => 5776 / 111
       **/
      "mul": function(a, b) {
        parse(a, b);
        return newFraction(
          this["s"] * P["s"] * this["n"] * P["n"],
          this["d"] * P["d"]
        );
      },
      /**
       * Divides two rational numbers
       *
       * Ex: new Fraction("-17.(345)").inverse().div(3)
       **/
      "div": function(a, b) {
        parse(a, b);
        return newFraction(
          this["s"] * P["s"] * this["n"] * P["d"],
          this["d"] * P["n"]
        );
      },
      /**
       * Clones the actual object
       *
       * Ex: new Fraction("-17.(345)").clone()
       **/
      "clone": function() {
        return newFraction(this["s"] * this["n"], this["d"]);
      },
      /**
       * Calculates the modulo of two rational numbers - a more precise fmod
       *
       * Ex: new Fraction('4.(3)').mod([7, 8]) => (13/3) % (7/8) = (5/6)
       * Ex: new Fraction(20, 10).mod().equals(0) ? "is Integer"
       **/
      "mod": function(a, b) {
        if (a === void 0) {
          return newFraction(this["s"] * this["n"] % this["d"], C_ONE);
        }
        parse(a, b);
        if (C_ZERO === P["n"] * this["d"]) {
          throw DivisionByZero();
        }
        return newFraction(
          this["s"] * (P["d"] * this["n"]) % (P["n"] * this["d"]),
          P["d"] * this["d"]
        );
      },
      /**
       * Calculates the fractional gcd of two rational numbers
       *
       * Ex: new Fraction(5,8).gcd(3,7) => 1/56
       */
      "gcd": function(a, b) {
        parse(a, b);
        return newFraction(gcd(P["n"], this["n"]) * gcd(P["d"], this["d"]), P["d"] * this["d"]);
      },
      /**
       * Calculates the fractional lcm of two rational numbers
       *
       * Ex: new Fraction(5,8).lcm(3,7) => 15
       */
      "lcm": function(a, b) {
        parse(a, b);
        if (P["n"] === C_ZERO && this["n"] === C_ZERO) {
          return newFraction(C_ZERO, C_ONE);
        }
        return newFraction(P["n"] * this["n"], gcd(P["n"], this["n"]) * gcd(P["d"], this["d"]));
      },
      /**
       * Gets the inverse of the fraction, means numerator and denominator are exchanged
       *
       * Ex: new Fraction([-3, 4]).inverse() => -4 / 3
       **/
      "inverse": function() {
        return newFraction(this["s"] * this["d"], this["n"]);
      },
      /**
       * Calculates the fraction to some integer exponent
       *
       * Ex: new Fraction(-1,2).pow(-3) => -8
       */
      "pow": function(a, b) {
        parse(a, b);
        if (P["d"] === C_ONE) {
          if (P["s"] < C_ZERO) {
            return newFraction((this["s"] * this["d"]) ** P["n"], this["n"] ** P["n"]);
          } else {
            return newFraction((this["s"] * this["n"]) ** P["n"], this["d"] ** P["n"]);
          }
        }
        if (this["s"] < C_ZERO) return null;
        let N2 = factorize(this["n"]);
        let D = factorize(this["d"]);
        let n = C_ONE;
        let d2 = C_ONE;
        for (let k in N2) {
          if (k === "1") continue;
          if (k === "0") {
            n = C_ZERO;
            break;
          }
          N2[k] *= P["n"];
          if (N2[k] % P["d"] === C_ZERO) {
            N2[k] /= P["d"];
          } else return null;
          n *= BigInt(k) ** N2[k];
        }
        for (let k in D) {
          if (k === "1") continue;
          D[k] *= P["n"];
          if (D[k] % P["d"] === C_ZERO) {
            D[k] /= P["d"];
          } else return null;
          d2 *= BigInt(k) ** D[k];
        }
        if (P["s"] < C_ZERO) {
          return newFraction(d2, n);
        }
        return newFraction(n, d2);
      },
      /**
       * Calculates the logarithm of a fraction to a given rational base
       *
       * Ex: new Fraction(27, 8).log(9, 4) => 3/2
       */
      "log": function(a, b) {
        parse(a, b);
        if (this["s"] <= C_ZERO || P["s"] <= C_ZERO) return null;
        const allPrimes = /* @__PURE__ */ Object.create(null);
        const baseFactors = factorize(P["n"]);
        const T1 = factorize(P["d"]);
        const numberFactors = factorize(this["n"]);
        const T2 = factorize(this["d"]);
        for (const prime in T1) {
          baseFactors[prime] = (baseFactors[prime] || C_ZERO) - T1[prime];
        }
        for (const prime in T2) {
          numberFactors[prime] = (numberFactors[prime] || C_ZERO) - T2[prime];
        }
        for (const prime in baseFactors) {
          if (prime === "1") continue;
          allPrimes[prime] = true;
        }
        for (const prime in numberFactors) {
          if (prime === "1") continue;
          allPrimes[prime] = true;
        }
        let retN = null;
        let retD = null;
        for (const prime in allPrimes) {
          const baseExponent = baseFactors[prime] || C_ZERO;
          const numberExponent = numberFactors[prime] || C_ZERO;
          if (baseExponent === C_ZERO) {
            if (numberExponent !== C_ZERO) {
              return null;
            }
            continue;
          }
          let curN = numberExponent;
          let curD = baseExponent;
          const gcdValue = gcd(curN, curD);
          curN /= gcdValue;
          curD /= gcdValue;
          if (retN === null && retD === null) {
            retN = curN;
            retD = curD;
          } else if (curN * retD !== retN * curD) {
            return null;
          }
        }
        return retN !== null && retD !== null ? newFraction(retN, retD) : null;
      },
      /**
       * Check if two rational numbers are the same
       *
       * Ex: new Fraction(19.6).equals([98, 5]);
       **/
      "equals": function(a, b) {
        parse(a, b);
        return this["s"] * this["n"] * P["d"] === P["s"] * P["n"] * this["d"];
      },
      /**
       * Check if this rational number is less than another
       *
       * Ex: new Fraction(19.6).lt([98, 5]);
       **/
      "lt": function(a, b) {
        parse(a, b);
        return this["s"] * this["n"] * P["d"] < P["s"] * P["n"] * this["d"];
      },
      /**
       * Check if this rational number is less than or equal another
       *
       * Ex: new Fraction(19.6).lt([98, 5]);
       **/
      "lte": function(a, b) {
        parse(a, b);
        return this["s"] * this["n"] * P["d"] <= P["s"] * P["n"] * this["d"];
      },
      /**
       * Check if this rational number is greater than another
       *
       * Ex: new Fraction(19.6).lt([98, 5]);
       **/
      "gt": function(a, b) {
        parse(a, b);
        return this["s"] * this["n"] * P["d"] > P["s"] * P["n"] * this["d"];
      },
      /**
       * Check if this rational number is greater than or equal another
       *
       * Ex: new Fraction(19.6).lt([98, 5]);
       **/
      "gte": function(a, b) {
        parse(a, b);
        return this["s"] * this["n"] * P["d"] >= P["s"] * P["n"] * this["d"];
      },
      /**
       * Compare two rational numbers
       * < 0 iff this < that
       * > 0 iff this > that
       * = 0 iff this = that
       *
       * Ex: new Fraction(19.6).compare([98, 5]);
       **/
      "compare": function(a, b) {
        parse(a, b);
        let t = this["s"] * this["n"] * P["d"] - P["s"] * P["n"] * this["d"];
        return (C_ZERO < t) - (t < C_ZERO);
      },
      /**
       * Calculates the ceil of a rational number
       *
       * Ex: new Fraction('4.(3)').ceil() => (5 / 1)
       **/
      "ceil": function(places) {
        places = C_TEN ** BigInt(places || 0);
        return newFraction(
          ifloor(this["s"] * places * this["n"] / this["d"]) + (places * this["n"] % this["d"] > C_ZERO && this["s"] >= C_ZERO ? C_ONE : C_ZERO),
          places
        );
      },
      /**
       * Calculates the floor of a rational number
       *
       * Ex: new Fraction('4.(3)').floor() => (4 / 1)
       **/
      "floor": function(places) {
        places = C_TEN ** BigInt(places || 0);
        return newFraction(
          ifloor(this["s"] * places * this["n"] / this["d"]) - (places * this["n"] % this["d"] > C_ZERO && this["s"] < C_ZERO ? C_ONE : C_ZERO),
          places
        );
      },
      /**
       * Rounds a rational numbers
       *
       * Ex: new Fraction('4.(3)').round() => (4 / 1)
       **/
      "round": function(places) {
        places = C_TEN ** BigInt(places || 0);
        return newFraction(
          ifloor(this["s"] * places * this["n"] / this["d"]) + this["s"] * ((this["s"] >= C_ZERO ? C_ONE : C_ZERO) + C_TWO * (places * this["n"] % this["d"]) > this["d"] ? C_ONE : C_ZERO),
          places
        );
      },
      /**
        * Rounds a rational number to a multiple of another rational number
        *
        * Ex: new Fraction('0.9').roundTo("1/8") => 7 / 8
        **/
      "roundTo": function(a, b) {
        parse(a, b);
        const n = this["n"] * P["d"];
        const d2 = this["d"] * P["n"];
        const r = n % d2;
        let k = ifloor(n / d2);
        if (r + r >= d2) {
          k++;
        }
        return newFraction(this["s"] * k * P["n"], P["d"]);
      },
      /**
       * Check if two rational numbers are divisible
       *
       * Ex: new Fraction(19.6).divisible(1.5);
       */
      "divisible": function(a, b) {
        parse(a, b);
        if (P["n"] === C_ZERO) return false;
        return this["n"] * P["d"] % (P["n"] * this["d"]) === C_ZERO;
      },
      /**
       * Returns a decimal representation of the fraction
       *
       * Ex: new Fraction("100.'91823'").valueOf() => 100.91823918239183
       **/
      "valueOf": function() {
        return Number(this["s"] * this["n"]) / Number(this["d"]);
      },
      /**
       * Creates a string representation of a fraction with all digits
       *
       * Ex: new Fraction("100.'91823'").toString() => "100.(91823)"
       **/
      "toString": function(dec = 15) {
        let N2 = this["n"];
        let D = this["d"];
        let cycLen = cycleLen(N2, D);
        let cycOff = cycleStart(N2, D, cycLen);
        let str = this["s"] < C_ZERO ? "-" : "";
        str += ifloor(N2 / D);
        N2 %= D;
        N2 *= C_TEN;
        if (N2)
          str += ".";
        if (cycLen) {
          for (let i = cycOff; i--; ) {
            str += ifloor(N2 / D);
            N2 %= D;
            N2 *= C_TEN;
          }
          str += "(";
          for (let i = cycLen; i--; ) {
            str += ifloor(N2 / D);
            N2 %= D;
            N2 *= C_TEN;
          }
          str += ")";
        } else {
          for (let i = dec; N2 && i--; ) {
            str += ifloor(N2 / D);
            N2 %= D;
            N2 *= C_TEN;
          }
        }
        return str;
      },
      /**
       * Returns a string-fraction representation of a Fraction object
       *
       * Ex: new Fraction("1.'3'").toFraction() => "4 1/3"
       **/
      "toFraction": function(showMixed = false) {
        let n = this["n"];
        let d2 = this["d"];
        let str = this["s"] < C_ZERO ? "-" : "";
        if (d2 === C_ONE) {
          str += n;
        } else {
          const whole = ifloor(n / d2);
          if (showMixed && whole > C_ZERO) {
            str += whole;
            str += " ";
            n %= d2;
          }
          str += n;
          str += "/";
          str += d2;
        }
        return str;
      },
      /**
       * Returns a latex representation of a Fraction object
       *
       * Ex: new Fraction("1.'3'").toLatex() => "\frac{4}{3}"
       **/
      "toLatex": function(showMixed = false) {
        let n = this["n"];
        let d2 = this["d"];
        let str = this["s"] < C_ZERO ? "-" : "";
        if (d2 === C_ONE) {
          str += n;
        } else {
          const whole = ifloor(n / d2);
          if (showMixed && whole > C_ZERO) {
            str += whole;
            n %= d2;
          }
          str += "\\frac{";
          str += n;
          str += "}{";
          str += d2;
          str += "}";
        }
        return str;
      },
      /**
       * Returns an array of continued fraction elements
       *
       * Ex: new Fraction("7/8").toContinued() => [0,1,7]
       */
      "toContinued": function() {
        let a = this["n"];
        let b = this["d"];
        const res = [];
        while (b) {
          res.push(ifloor(a / b));
          const t = a % b;
          a = b;
          b = t;
        }
        return res;
      },
      "simplify": function(eps = 1e-3) {
        const ieps = BigInt(Math.ceil(1 / eps));
        const thisABS = this["abs"]();
        const cont = thisABS["toContinued"]();
        for (let i = 1; i < cont.length; i++) {
          let s = newFraction(cont[i - 1], C_ONE);
          for (let k = i - 2; k >= 0; k--) {
            s = s["inverse"]()["add"](cont[k]);
          }
          let t = s["sub"](thisABS);
          if (t["n"] * ieps < t["d"]) {
            return s["mul"](this["s"]);
          }
        }
        return this;
      }
    };
  }
});

// outputs/skycam/labs/strudel/node_modules/@kabelsalat/web/dist/index.js
var kabelsalat;
var init_dist = __esm({
  "outputs/skycam/labs/strudel/node_modules/@kabelsalat/web/dist/index.js"() {
    kabelsalat = (function(l2) {
      "use strict";
      function T(e, t) {
        if (t || (t = "assertion failed"), !e) throw new Error(t);
      }
      class u {
        constructor(t, i) {
          this.type = t, i !== void 0 && (this.value = i), this.ins = [];
        }
        static parseInput(t, i) {
          if (typeof t == "function") {
            if (!i) throw new Error("tried to parse function input without without passing node..");
            return t(i);
          }
          return typeof t == "object" ? t : typeof t == "number" && !isNaN(t) || typeof t == "string" ? X(t) : (console.log(`invalid input type "${typeof t}" for node of type "${i.type}", falling back to 0. The input was:`, t), 0);
        }
      }
      const R2 = (e, t) => new u(e, t);
      let r = /* @__PURE__ */ new Map();
      const b = "poly", V2 = "exit";
      u.prototype.inherit = function(e) {
        return e.inputOf && (this.inputOf = e.inputOf), e.outputOf && (this.outputOf = e.outputOf), this;
      }, u.prototype.toObject = function() {
        return JSON.parse(JSON.stringify(this));
      }, u.prototype.stringify = function() {
        return JSON.stringify(this, null, 2).replaceAll('"', "'");
      };
      function K2(e, ...t) {
        let i = 1;
        if (t = t.map((s) => {
          if (Array.isArray(s)) {
            if (s.length === 1) return s[0];
            s = new u(b).withIns(...s);
          }
          if (typeof s == "function") {
            const d2 = s(new u("peek"));
            d2.type === b && (i = Math.max(d2.ins.length, i));
          }
          return s.type === b && (i = Math.max(s.ins.length, i)), s;
        }), i === 1) {
          const s = R2(e);
          return s.withIns(...t.map((d2) => u.parseInput(d2, s)));
        }
        if (e === V2) {
          const s = t.map((d2) => d2.type === b ? d2.ins.map((c2) => u.parseInput(c2).inherit(c2)) : d2).flat();
          return R2(V2).withIns(...s);
        }
        const n = Array.from({ length: i }, (s, d2) => {
          const c2 = new u(e), f2 = t.map((p) => p.type === b ? u.parseInput(p.ins[d2 % p.ins.length], c2).inherit(p) : (p = u.parseInput(p, c2), p.type === b && (p = p.ins[d2]), p));
          return c2.withIns(...f2);
        });
        return new u(b).withIns(...n);
      }
      function q2(e, t) {
        const i = r.get(e);
        return i?.ins?.[t] ? i.ins[t].name : "";
      }
      let o = (e, t) => m2(e, (...i) => K2(e, ...i), t);
      r.set("register", { tags: ["meta"], graph: false, description: "Registers a new Node function. Sets it on the prototype + returns the function itself. Like `module` but doesn't hide complexity in graph viz.", examples: [`let kick = register('kick', gate => gate.adsr(0,.11,0,.11)
.apply(env => env.mul(env)
  .mul(158)
  .sine(env)
  .distort(.85)
))
impulse(2).kick().out()`] });
      let m2 = (e, t, i) => (i && r.set(e, i), u.prototype[e] = function(...n) {
        return t(this, ...n);
      }, u.prototype["_" + e] = function() {
        return this;
      }, t);
      r.set("module", { tags: ["meta"], graph: true, description: "Creates a module. Like `register`, but the graph viz will hide the internal complexity of the module.", examples: [`let kick = module('kick', gate => gate.adsr(0,.11,0,.11)
.apply(env => env.mul(env)
  .mul(158)
  .sine(env)
  .distort(.85)
))
impulse(2).kick().out()`] });
      let Qt = 0;
      function g(e, t, i) {
        return m2(e, (...n) => {
          const s = Qt++;
          return n = n.map((d2, c2) => u.parseInput(d2).asModuleInput?.(e, s, c2)), t(...n).asModuleOutput?.(e, s);
        }, i);
      }
      r.set("n", { tags: ["math"], description: "Constant value node. Turns a number into a Node.", ins: [{ name: "value", default: 0 }] });
      function X(e) {
        return Array.isArray(e) ? poly(...e.map((t) => X(t))) : typeof e == "object" ? e : R2("n", e);
      }
      r.set("out", { tags: ["meta"], description: "Sends the node to the audio output" }), r.set("withIns", { internal: true, tags: ["innards"], description: "Sets the inputs of a node. Returns the node itself", ins: [{ name: "in", dynamic: true }] }), u.prototype.withIns = function(...e) {
        return this.ins = e, this;
      }, r.set("flatten", { internal: true, tags: ["innards"], description: "Flattens the node to a list of all nodes in the graph, where each Node's ins are now indices" }), u.prototype.flatten = function() {
        return Bt2(this);
      }, r.set("apply", { graph: true, tags: ["meta"], description: "Applies the given function to the Node. Useful when a node has to be used multiple times.", examples: [`impulse(4)
.apply(imp=>imp
  .seq(110,220,330,440)
  .sine()
  .mul( imp.ad(.1,.1) )
).out()`] }), u.prototype.apply = function(e) {
        return e(this);
      }, r.set("clone", { internal: true, tags: ["innards"], description: "Clones the node" }), u.prototype.clone = function() {
        return new u(this.type, this.value).withIns(...this.ins);
      }, r.set("map", { tags: ["meta"], description: "Applies the given function to all ins if it's poly node. Otherwise it applies the function to itself.", examples: [`n([110,220,330])
.map( freq=>freq.mul([1,1.007]).saw().mix() )
.mix(2).mul(.5).out()`] }), u.prototype.map = function(e) {
        return this.type !== "poly" ? e(this) : poly(...this.ins.map(e));
      }, u.prototype.channel = function(e) {
        return this.type !== "poly" ? this : this.ins[e % this.ins.length];
      }, r.set("select", { tags: ["meta"], graph: true, description: "Find the first occurence of the given type up in the graph and returns the match. Useful to exit a feedback loop at another point.", examples: [`sine(220).mul(impulse(1).ad(.001,.2))
.add( x=>x.delay(.2).mul(.8) )
.select('delay').out()
`] }), u.prototype.select = function(e) {
        for (let t of this.ins) {
          if (t.type === e) return t;
          const i = t.select(e);
          if (i) return i;
        }
      }, r.set("debug", { tags: ["meta"], description: "Logs the node to the console" }), u.prototype.debug = function(e = (t) => t) {
        return console.log(e(this)), this;
      };
      function _(e) {
        const t = modules.get(e), i = Array.from({ length: t.length }, (s, d2) => R2(`$INPUT${d2}`)), n = t(...i);
        return JSON.stringify(n, null, 2);
      }
      function Bt2(e) {
        const t = [];
        return I(e, (i) => (t.push(i), i)), t.map((i) => {
          let n = { ...i, type: i.type, ins: i.ins.map((s) => t.indexOf(s) + "") };
          return i.value !== void 0 && (n.value = i.value), i.to !== void 0 && (n.to = t.indexOf(i.to)), n;
        });
      }
      let C2 = o("exit", { internal: true });
      function v(e, t) {
        let i = [];
        const n = m2("out", function(d2, c2 = [0, 1]) {
          return i.push(d2.output(c2)), d2;
        });
        return t ? (t.out = n, Function(...Object.keys(t), e)(...Object.values(t))) : (globalThis.out = n, Function(e)()), C2(...i);
      }
      u.prototype.over = function(e) {
        return this.apply((t) => add(t, e(t)));
      }, u.prototype.dfs = function(e, t) {
        return this.apply((i) => I(i, e, t));
      }, u.prototype.apply2 = function(e) {
        return e(this, this);
      };
      let I = (e, t, i = []) => (e = t(e, i), i.push(e), e.ins = e.ins.map((n) => i.includes(n) ? n : I(n, t, i)), e);
      u.prototype.asModuleInput = function(e, t, i) {
        return this.inputOf = this.inputOf || [], this.inputOf.push([e, t, i]), this;
      }, u.prototype.asModuleOutput = function(e, t) {
        return this.outputOf = [e, t], this;
      };
      function W2(e, t = {}) {
        const { log: i = false, lang: n = "js", fallbackType: s = "thru", constType: d2 = "n", getRegister: c2 = (y) => `r[${y}]`, getOutput: f2 = (y) => `o[${y}]`, getSource: p = (y) => `s[${y}]` } = t;
        i && console.log("compile", e);
        const h = Et2(e);
        let G2 = [], z2 = (y) => h[y].type !== d2 ? c2(y) : typeof h[y].value == "string" ? `"${h[y].value}"` : h[y].value;
        const Z2 = [];
        for (let y in h) {
          const Jt2 = h[y], jt2 = h[y].ins.map((Bi2) => z2(h.indexOf(Bi2))), ji2 = Z2.length;
          let M = r.get(Jt2.type);
          M || (console.warn(`unhandled node type "${h[y].type}". falling back to "${s}"`), M = r.get(s));
          const Qi2 = { vars: jt2, node: Jt2, nodes: h, id: y, ugenIndex: ji2, ugen: M.ugen, name: z2(y), lang: n, getRegister: c2, getOutput: f2, getSource: p };
          M.compile && G2.push(M.compile(Qi2)), M.ugen && Z2.push({ type: M.ugen, inputs: jt2 });
        }
        const w2 = G2.join(`
`);
        return i && (console.log("compiled code:"), console.log(w2)), { src: w2, ugens: Z2, registers: h.length };
      }
      u.prototype.compile = function(e) {
        return W2(this, e);
      };
      function Et2(e) {
        const t = [], i = /* @__PURE__ */ new Set();
        function n(s) {
          if (!(typeof s != "object" || i.has(s))) {
            i.add(s);
            for (let d2 in s.ins) n(s.ins[d2]);
            t.push(s);
          }
        }
        return n(e), t;
      }
      const ee2 = Object.freeze(Object.defineProperty({ __proto__: null, compile: W2 }, Symbol.toStringTag, { value: "Module" }));
      class te2 {
        constructor() {
          this._events = {};
        }
        on(t, i) {
          this._events[t] || (this._events[t] = []);
          let n = this._events[t];
          T(n.indexOf(i) == -1), n.push(i);
        }
        removeListener(t, i) {
          let n = this._events[t], s = n.indexOf(i);
          s != -1 && n.splice(s, 1);
        }
        trigger(t, ...i) {
          let n = this._events[t] || [];
          for (let s = 0; s < n.length; s++) n[s].apply(null, i);
        }
      }
      class Ot2 extends te2 {
        constructor(t = navigator) {
          super(), this.midiAccess = null, this.getMIDIAccess(t);
        }
        async getMIDIAccess(t) {
          if ("requestMIDIAccess" in t) {
            this.midiAccess = await t.requestMIDIAccess({ sysex: false }), console.log("got MIDI access");
            for (let i of this.midiAccess.inputs.values()) i.state == "connected" && (i.onmidimessage = (n) => this.trigger("midimessage", i.id, n.data));
            this.midiAccess.onstatechange = (i) => {
              i.port.type == "input" && i.port.state == "connected" && (console.log("MIDI device connected:", i.port.name, "PORT:", i.port.id), i.port.onmidimessage = (n) => this.trigger("midimessage", i.port.id, n.data));
            };
          }
        }
        broadcast(t, i) {
          if (midi) for (let n of this.midiAccess.outputs.values()) n.send(t, i);
        }
      }
      function $t2(e) {
        let t = e[0] & 240, i = (e[0] & 15) + 1;
        if (t == 176 && e.length == 3) {
          let n = e[1], d2 = e[2] / 127 * 2 - 1;
          return { type: "CC", channel: i, cc: n, value: d2 };
        }
        if (t == 224 && e.length == 3) {
          let n = e[1], c2 = (e[2] << 7 | n) / 16383 * 2 - 1;
          return { type: "PITCHBEND", channel: i, value: c2 };
        }
        if (t == 144 && e.length == 3) {
          let n = e[1], s = e[2] / 127;
          return { type: "NOTE_ON", channel: i, note: n, velocity: s };
        }
        if (t == 128 && e.length == 3) {
          let n = e[1];
          return { type: "NOTE_ON", channel: i, note: n, velocity: 0 };
        }
      }
      class At extends te2 {
        constructor() {
          super(), this.attach();
        }
        attach() {
          typeof window < "u" && (this.handleMouseMove = (t) => {
            const i = t.clientX / document.body.clientWidth * 2 - 1, n = t.clientY / document.body.clientHeight * 2 - 1;
            this.trigger("move", i, n);
          }, document.addEventListener("mousemove", this.handleMouseMove));
        }
        detach() {
          typeof window < "u" && document.removeEventListener("mousemove", this.handleMouseMove);
        }
      }
      const Dt = "data:text/javascript;base64,KGZ1bmN0aW9uKCl7InVzZSBzdHJpY3QiO2Z1bmN0aW9uIGcoaCx0KXtpZih0fHwodD0iYXNzZXJ0aW9uIGZhaWxlZCIpLCFoKXRocm93IG5ldyBFcnJvcih0KX1mdW5jdGlvbiBTKGgsdCxzKXtyZXR1cm4gaDw9MD90Omg+PTE/czp0K2gqKHMtdCl9ZnVuY3Rpb24gUChoLHQscyl7cmV0dXJuIGg8PXQ/MDpoPj1zPzE6cz09PXQ/MDooaC10KS8ocy10KX1mdW5jdGlvbiBFKGgsdCl7cmV0dXJuIGg8dD8oaC89dCxoK2gtaCpoLTEpOmg+MS10PyhoPShoLTEpL3QsaCpoK2graCsxKTowfWZ1bmN0aW9uIFUoaCl7cmV0dXJuIE1hdGguZmxvb3IoaCk9PT1ofWZ1bmN0aW9uIF8oaCl7cmV0dXJuIFUoaCkmJmg+MH1mdW5jdGlvbiBrKGgsdCl7dD1NYXRoLm1pbihNYXRoLm1heCh0LDApLDEpLHQtPS4wMTt2YXIgcz0yKnQvKDEtdCksZT0oMStzKSpoLygxK3MqTWF0aC5hYnMoaCkpO3JldHVybiBlfWZ1bmN0aW9uIHcoaCx0LHMpe3JldHVybiBoPj0xP3M6dCtoKihzLXQpfWZ1bmN0aW9uIFQoKXt0aGlzLnN0YXRlPSJvZmYiLHRoaXMuc3RhcnRUaW1lPTAsdGhpcy5zdGFydFZhbD0wfVQucHJvdG90eXBlLmV2YWw9ZnVuY3Rpb24oaCx0LHMsZSxpLG4pe3N3aXRjaCh0aGlzLnN0YXRlKXtjYXNlIm9mZiI6cmV0dXJuIHQ+MCYmKHRoaXMuc3RhdGU9ImF0dGFjayIsdGhpcy5zdGFydFRpbWU9aCx0aGlzLnN0YXJ0VmFsPTApLDA7Y2FzZSJhdHRhY2siOntsZXQgcj1oLXRoaXMuc3RhcnRUaW1lO3JldHVybiByPnM/KHRoaXMuc3RhdGU9ImRlY2F5Iix0aGlzLnN0YXJ0VGltZT1oLDEpOncoci9zLHRoaXMuc3RhcnRWYWwsMSl9Y2FzZSJkZWNheSI6e2xldCByPWgtdGhpcy5zdGFydFRpbWUsbD13KHIvZSwxLGkpO3JldHVybiB0PD0wPyh0aGlzLnN0YXRlPSJyZWxlYXNlIix0aGlzLnN0YXJ0VGltZT1oLHRoaXMuc3RhcnRWYWw9bCxsKTpyPmU/KHRoaXMuc3RhdGU9InN1c3RhaW4iLHRoaXMuc3RhcnRUaW1lPWgsaSk6bH1jYXNlInN1c3RhaW4iOnJldHVybiB0PD0wJiYodGhpcy5zdGF0ZT0icmVsZWFzZSIsdGhpcy5zdGFydFRpbWU9aCx0aGlzLnN0YXJ0VmFsPWkpLGk7Y2FzZSJyZWxlYXNlIjp7bGV0IHI9aC10aGlzLnN0YXJ0VGltZTtpZihyPm4pcmV0dXJuIHRoaXMuc3RhdGU9Im9mZiIsMDtsZXQgbD13KHIvbix0aGlzLnN0YXJ0VmFsLDApO3JldHVybiB0PjAmJih0aGlzLnN0YXRlPSJhdHRhY2siLHRoaXMuc3RhcnRUaW1lPWgsdGhpcy5zdGFydFZhbD1sKSxsfX10aHJvdyJpbnZhbGlkIGVudmVsb3BlIHN0YXRlIn07ZnVuY3Rpb24gdigpe3RoaXMuczA9MCx0aGlzLnMxPTB9di5wcm90b3R5cGUuYXBwbHk9ZnVuY3Rpb24oaCx0LHMpe2coIWlzTmFOKGgpLCJOYU4gdmFsdWUgZmVkIGluIFR3b1BvbGVGaWx0ZXIiKSx0PU1hdGgubWluKHQsMSkscz1NYXRoLm1heChzLDApO3ZhciBlPU1hdGgucG93KC41LCgxLXQpLy4xMjUpLGk9TWF0aC5wb3coLjUsKHMrLjEyNSkvLjEyNSksbj0xLWkqZSxyPXRoaXMuczAsbD10aGlzLnMxO3JldHVybiByPW4qci1lKmwrZSpoLGw9bipsK2UqcixoPWwsdGhpcy5zMD1yLHRoaXMuczE9bCxofTtsZXQgQT1jbGFzcyBDe2NvbnN0cnVjdG9yKHQscyl7dGhpcy5zYW1wbGVSYXRlPXQscz90aGlzLmJ1ZmZlcj1zLnNsaWNlKDApOih0aGlzLmJ1ZmZlcj1uZXcgRmxvYXQzMkFycmF5KDEwKnQpLHRoaXMuYnVmZmVyLmZpbGwoMCkpLHRoaXMud3JpdGVJZHg9MCx0aGlzLnJlYWRJZHg9MH1yZXNldCgpe3RoaXMuYnVmZmVyLmZpbGwoMCksdGhpcy53cml0ZUlkeD0wLHRoaXMucmVhZElkeD0wfWNsb25lKCl7Y29uc3QgdD1uZXcgQyh0aGlzLnNhbXBsZVJhdGUsdGhpcy5idWZmZXIpO3JldHVybiB0LndyaXRlSWR4PXRoaXMud3JpdGVJZHgsdC5yZWFkSWR4PXRoaXMucmVhZElkeCx0fXdyaXRlKHQscyl7dGhpcy53cml0ZUlkeD0odGhpcy53cml0ZUlkeCsxKSV0aGlzLmJ1ZmZlci5sZW5ndGgsdGhpcy5idWZmZXJbdGhpcy53cml0ZUlkeF09dDtsZXQgZT1NYXRoLm1pbihNYXRoLmZsb29yKHRoaXMuc2FtcGxlUmF0ZSpzKSx0aGlzLmJ1ZmZlci5sZW5ndGgtMSk7dGhpcy5yZWFkSWR4PXRoaXMud3JpdGVJZHgtZSx0aGlzLnJlYWRJZHg8MCYmKHRoaXMucmVhZElkeCs9dGhpcy5idWZmZXIubGVuZ3RoKX1yZWFkKCl7cmV0dXJuIHRoaXMuYnVmZmVyW3RoaXMucmVhZElkeF19fTtjb25zdCB5PTEvNDhlMyxNPTI0LE49TS80O2NsYXNzIG97Y29uc3RydWN0b3IodCxzLGUsaSl7dGhpcy5ub2RlSWQ9dCx0aGlzLnN0YXRlPXMsdGhpcy5zYW1wbGVSYXRlPWUsdGhpcy5zYW1wbGVUaW1lPTEvZSx0aGlzLnNlbmQ9aX19Y2xhc3MgcSBleHRlbmRzIG97Y29uc3RydWN0b3IodCxzLGUsaSl7c3VwZXIodCxzLGUsaSksdGhpcy5lbnY9bmV3IFR9dXBkYXRlKHQscyxlLGksbixyKXtyZXR1cm4gdGhpcy5lbnYuZXZhbCh0LHMsZSxpLG4scil9fWNsYXNzIEYgZXh0ZW5kcyBve2NvbnN0cnVjdG9yKHQscyxlLGkpe3N1cGVyKHQscyxlLGkpLHRoaXMucGhhc2U9MH11cGRhdGUodCl7bGV0IHM9TSp0LzYwLGU9LjU7cmV0dXJuIHRoaXMucGhhc2UrPXRoaXMuc2FtcGxlVGltZSpzLHRoaXMucGhhc2UlMTxlPzE6LTF9fWNsYXNzIEQgZXh0ZW5kcyBve2NvbnN0cnVjdG9yKHQscyxlLGkpe3N1cGVyKHQscyxlLGkpLHRoaXMuaW5TZ249ITAsdGhpcy5vdXRTZ249ITAsdGhpcy5jbG9ja0NudD0wfXVwZGF0ZSh0LHMpe2xldCBlPXQ+MDtyZXR1cm4gdGhpcy5pblNnbiE9ZSYmKHRoaXMuY2xvY2tDbnQrKyx0aGlzLmNsb2NrQ250Pj1zJiYodGhpcy5jbG9ja0NudD0wLHRoaXMub3V0U2duPSF0aGlzLm91dFNnbikpLHRoaXMuaW5TZ249ZSx0aGlzLm91dFNnbj8xOi0xfX1jbGFzcyBMIGV4dGVuZHMgb3tjb25zdHJ1Y3Rvcih0LHMsZSxpKXtzdXBlcih0LHMsZSxpKSx0aGlzLmluU2duPSExfXVwZGF0ZSh0LHMpe2xldCBlPXM+MDtyZXR1cm4gZSYmdGhpcy5pblNnbiE9ZSYmdGhpcy5zZW5kKHt0eXBlOiJDTE9DS19QVUxTRSIsbm9kZUlkOnRoaXMubm9kZUlkLHRpbWU6dH0pLHRoaXMuaW5TZ249ZSwwfX1jb25zdCBPPW5ldyBNYXA7Y2xhc3MgViBleHRlbmRzIG97Y29uc3RydWN0b3IodCxzLGUsaSl7c3VwZXIodCxzLGUsaSk7Y29uc3Qgbj1zLmlucHV0c1syXTtuJiZPLmhhcyhuKT90aGlzLmRlbGF5PU8uZ2V0KG4pLmNsb25lKCk6dGhpcy5kZWxheT1uZXcgQShlKSxuJiZPLnNldChuLHRoaXMuZGVsYXkpfXVwZGF0ZSh0LHMpe3JldHVybiB0aGlzLmRlbGF5LndyaXRlKHQscyksdGhpcy5kZWxheS5yZWFkKCl9fWNsYXNzIEcgZXh0ZW5kcyBve2NvbnN0cnVjdG9yKHQscyxlLGkpe3N1cGVyKHQscyxlLGkpfXVwZGF0ZSh0LHMpe3JldHVybiBrKHQscyl9fWNsYXNzIFIgZXh0ZW5kcyBve2NvbnN0cnVjdG9yKHQscyxlLGkpe3N1cGVyKHQscyxlLGkpLHRoaXMudmFsdWU9MCx0aGlzLnRyaWdTZ249ITF9d3JpdGUodCxzKXshdGhpcy50cmlnU2duJiZzPjAmJih0aGlzLnZhbHVlPXQpLHRoaXMudHJpZ1Nnbj1zPjB9cmVhZCgpe3JldHVybiB0aGlzLnZhbHVlfXVwZGF0ZSh0LHMpe3JldHVybiB0aGlzLndyaXRlKHQscyksdGhpcy5yZWFkKCl9fWNsYXNzIEJ7Y29uc3RydWN0b3IoKXt0aGlzLnZhbHVlPTB9dXBkYXRlKHQpe3JldHVybiB0aGlzLnZhbHVlPXQsdGhpcy52YWx1ZX19Y29uc3QgJD0zNDA7bGV0IEk9MDtjbGFzcyBIe2NvbnN0cnVjdG9yKCl7dGhpcy5jaD1JLHRoaXMuc3RhcnRfc2VlZD0kKih0aGlzLmNoKzEpPj4+MCx0aGlzLnN0YXRlPXRoaXMuc3RhcnRfc2VlZCx0aGlzLnZhbHVlPTAsdGhpcy5hPTE2NjQ1MjUsdGhpcy5jPTEwMTM5MDQyMjMsdGhpcy5tYXNrPTE2Nzc3MjE1LHRoaXMuc2NhbGU9MS8oMTw8MjQpLEkrK311cGRhdGUodCxzKXtpZighdClyZXR1cm4gdGhpcy52YWx1ZTtzJiYodGhpcy5zdGF0ZT10aGlzLnN0YXJ0X3NlZWQpLHRoaXMuc3RhdGU9dGhpcy5zdGF0ZSp0aGlzLmErdGhpcy5jPj4+MDtjb25zdCBlPSh0aGlzLnN0YXRlJnRoaXMubWFzaykqdGhpcy5zY2FsZTtyZXR1cm4gdGhpcy52YWx1ZT1lKjItMSx0aGlzLnZhbHVlfX1jbGFzcyBqe2NvbnN0cnVjdG9yKCl7dGhpcy52YWx1ZT1NYXRoLnJhbmRvbSgpKjItMX11cGRhdGUodCl7cmV0dXJuIHQ/KHRoaXMudmFsdWU9TWF0aC5yYW5kb20oKSoyLTEsdGhpcy52YWx1ZSk6dGhpcy52YWx1ZX19Y2xhc3MgS3t1cGRhdGUodCl7cmV0dXJuIE1hdGgucmFuZG9tKCk8dCp5P01hdGgucmFuZG9tKCk6MH19Y2xhc3MgV3tjb25zdHJ1Y3Rvcigpe3RoaXMub3V0PTB9dXBkYXRlKCl7bGV0IHQ9TWF0aC5yYW5kb20oKSoyLTE7cmV0dXJuIHRoaXMub3V0PSh0aGlzLm91dCsuMDIqdCkvMS4wMix0aGlzLm91dH19Y2xhc3MgWHtjb25zdHJ1Y3Rvcigpe3RoaXMuYjA9MCx0aGlzLmIxPTAsdGhpcy5iMj0wLHRoaXMuYjM9MCx0aGlzLmI0PTAsdGhpcy5iNT0wLHRoaXMuYjY9MH11cGRhdGUoKXtjb25zdCB0PU1hdGgucmFuZG9tKCkqMi0xO3RoaXMuYjA9Ljk5ODg2KnRoaXMuYjArdCouMDU1NTE3OSx0aGlzLmIxPS45OTMzMip0aGlzLmIxK3QqLjA3NTA3NTksdGhpcy5iMj0uOTY5KnRoaXMuYjIrdCouMTUzODUyLHRoaXMuYjM9Ljg2NjUqdGhpcy5iMyt0Ki4zMTA0ODU2LHRoaXMuYjQ9LjU1KnRoaXMuYjQrdCouNTMyOTUyMix0aGlzLmI1PS0uNzYxNip0aGlzLmI1LXQqLjAxNjg5ODtjb25zdCBzPXRoaXMuYjArdGhpcy5iMSt0aGlzLmIyK3RoaXMuYjMrdGhpcy5iNCt0aGlzLmI1K3RoaXMuYjYrdCouNTM2MjtyZXR1cm4gdGhpcy5iNj10Ki4xMTU5MjYscyouMTF9fWNsYXNzIFkgZXh0ZW5kcyBve2NvbnN0cnVjdG9yKHQscyxlLGkpe3N1cGVyKHQscyxlLGkpLHRoaXMucGhhc2U9MX11cGRhdGUodCl7dGhpcy5waGFzZSs9dGhpcy5zYW1wbGVUaW1lKnQ7bGV0IHM9dGhpcy5waGFzZT49MT8xOjA7cmV0dXJuIHRoaXMucGhhc2U9dGhpcy5waGFzZSUxLHN9fWNsYXNzIHogZXh0ZW5kcyBve2NvbnN0cnVjdG9yKHQscyxlLGkpe3N1cGVyKHQscyxlLGkpLHRoaXMucGhhc2U9MH11cGRhdGUodCxzKXtyZXR1cm4gdGhpcy5waGFzZSs9dGhpcy5zYW1wbGVUaW1lKnQsdGhpcy5waGFzZSUxPHM/MTotMX19Y2xhc3MgWiBleHRlbmRzIG97Y29uc3RydWN0b3IodCxzLGUsaSl7c3VwZXIodCxzLGUsaSksdGhpcy5waGFzZT0wfXVwZGF0ZSh0KXtyZXR1cm4gdGhpcy5waGFzZSs9dGhpcy5zYW1wbGVUaW1lKnQsdGhpcy5waGFzZSUxKjItMX19Y2xhc3MgSntjb25zdHJ1Y3Rvcigpe3RoaXMucGhhc2U9TWF0aC5yYW5kb20oKX11cGRhdGUodCl7Y29uc3Qgcz10L3NhbXBsZVJhdGU7bGV0IGU9RSh0aGlzLnBoYXNlLHMpLGk9Mip0aGlzLnBoYXNlLTEtZTtyZXR1cm4gdGhpcy5waGFzZSs9cyx0aGlzLnBoYXNlPjEmJih0aGlzLnBoYXNlLT0xKSxpfX1jbGFzcyBRIGV4dGVuZHMgb3tjb25zdHJ1Y3Rvcih0LHMsZSxpKXtzdXBlcih0LHMsZSxpKSx0aGlzLnBoYXNlPTAsdGhpcy5zeW5jU2duPSExfXVwZGF0ZSh0LHMsZSl7IXRoaXMuc3luY1NnbiYmcz4wJiYodGhpcy5waGFzZT0wKSx0aGlzLnN5bmNTZ249cz4wO2xldCBpPSh0aGlzLnBoYXNlK2UpJTE7cmV0dXJuIHRoaXMucGhhc2UrPXRoaXMuc2FtcGxlVGltZSp0LE1hdGguc2luKGkqMipNYXRoLlBJKX19Y2xhc3MgdHR7ZEJUb0xpbmVhcih0KXtyZXR1cm4gTWF0aC5wb3coMTAsdC8yMCl9bGluZWFyVG9EQih0KXtyZXR1cm4gMjAqTWF0aC5sb2cxMCh0KX11cGRhdGUodCxzLGUpe2xldCBpPXRoaXMubGluZWFyVG9EQihNYXRoLmFicyh0KSksbj0wO3JldHVybiBpPnMmJihuPShpLXMpKigxLTEvZSkpLHRoaXMuZEJUb0xpbmVhcigtbil9fWNsYXNzIHN0IGV4dGVuZHMgb3tjb25zdHJ1Y3Rvcih0LHMsZSxpKXtzdXBlcih0LHMsZSxpKSx0aGlzLnBoYXNlPTB9dXBkYXRlKHQpe3RoaXMucGhhc2UrPXRoaXMuc2FtcGxlVGltZSp0O2xldCBzPXRoaXMucGhhc2UlMTtyZXR1cm4oczwuNT8yKnM6MS0yKihzLS41KSkqMi0xfX1jbGFzcyBldCBleHRlbmRzIG97Y29uc3RydWN0b3IodCxzLGUsaSl7c3VwZXIodCxzLGUsaSk7Y29uc3Qgbj1lLzMwO2coXyhuKSksdGhpcy5idWZmZXI9bmV3IEZsb2F0MzJBcnJheShuKSx0aGlzLndyaXRlUG9zPTB9dXBkYXRlKHQscyxlLGkpe3JldHVybiB0aGlzLmJ1ZmZlclt0aGlzLndyaXRlUG9zXT10LHRoaXMud3JpdGVQb3MrKyx0aGlzLndyaXRlUG9zJXRoaXMuYnVmZmVyLmxlbmd0aD09MCYmKHRoaXMud3JpdGVQb3M9MCx0aGlzLnNlbmQoe3R5cGU6IlNFTkRfU0FNUExFUyIsaWQ6cyxzYW1wbGVzOnRoaXMuYnVmZmVyLGNoYW5uZWxzOmUsY2hhbm5lbDppfSkpLHR9fWNsYXNzIGl0e2NvbnN0cnVjdG9yKCl7dGhpcy5sYWdVbml0PTQ0MTAsdGhpcy5zPTB9dXBkYXRlKHQscyl7cmV0dXJuIHM9cyp0aGlzLmxhZ1VuaXQsczwxJiYocz0xKSx0aGlzLnMrPTEvcyoodC10aGlzLnMpLHRoaXMuc319Y2xhc3MgaHR7Y29uc3RydWN0b3IoKXt0aGlzLmxhc3Q9MH11cGRhdGUodCxzLGUpe2NvbnN0IGk9cyp5LG49ZSp5O2xldCByPXQtdGhpcy5sYXN0O3JldHVybiByPmk/cj1pOnI8LW4mJihyPS1uKSx0aGlzLmxhc3QrPXIsdGhpcy5sYXN0fX1jbGFzcyBhdCBleHRlbmRzIG97Y29uc3RydWN0b3IodCxzLGUsaSl7c3VwZXIodCxzLGUsaSksdGhpcy5zPTB9dXBkYXRlKHQscyl7cmV0dXJuIHM9cyoxZTMsczwxJiYocz0xKSx0aGlzLnMrPTEvcyoodC10aGlzLnMpLHRoaXMuc319Y2xhc3MgbnQgZXh0ZW5kcyBve2NvbnN0cnVjdG9yKHQscyxlLGkpe3N1cGVyKHQscyxlLGkpLHRoaXMuZmlsdGVyPW5ldyB2fXVwZGF0ZSh0LHMsZSl7cmV0dXJuIHRoaXMuZmlsdGVyLmFwcGx5KHQscyxlKSx0aGlzLmZpbHRlci5zMX19Y2xhc3MgcnQgZXh0ZW5kcyBve2NvbnN0cnVjdG9yKHQscyxlLGkpe3N1cGVyKHQscyxlLGkpLHRoaXMuZmlsdGVyPW5ldyB2fXVwZGF0ZSh0LHMsZSl7cmV0dXJuIHRoaXMuZmlsdGVyLmFwcGx5KHQscyxlKSx0aGlzLmZpbHRlci5zMH19Y2xhc3MgdXQgZXh0ZW5kcyBve2NvbnN0cnVjdG9yKHQscyxlLGkpe3N1cGVyKHQscyxlLGkpfXVwZGF0ZSh0LHMpe3JldHVybiBzPDAmJihzPTApLHM9cysxLHQ9dCpzLDQqKE1hdGguYWJzKC4yNSp0Ky4yNS1NYXRoLnJvdW5kKC4yNSp0Ky4yNSkpLS4yNSl9fWNsYXNzIGx0IGV4dGVuZHMgb3t1cGRhdGUodCl7cmV0dXJuIHR9fWNsYXNzIG0gZXh0ZW5kcyBve2NvbnN0cnVjdG9yKHQscyxlLGkpe3N1cGVyKHQscyxlLGkpLHRoaXMubm90ZT0wLHRoaXMuZnJlcT0wLHRoaXMudmVsb2NpdHk9MCx0aGlzLmdhdGVTdGF0ZT0ib2ZmIix0aGlzLnR5cGU9Im1pZGlpbiIsdGhpcy5jaGFubmVsPS0xfWlzRnJlZSgpe3JldHVybiB0aGlzLmdhdGVTdGF0ZT09PSJvZmYifW5vdGVPbih0LHMpe3M+MD8odGhpcy5ub3RlPXQsdGhpcy52ZWxvY2l0eT1zLHRoaXMuZnJlcT0yKiooKHQtNjkpLzEyKSo0NDAsdGhpcy5nYXRlU3RhdGU9InByZXRyaWciKTp0aGlzLm5vdGVPZmYoKX1ub3RlT2ZmKCl7dGhpcy5ub3RlPTAsdGhpcy5nYXRlU3RhdGU9Im9mZiJ9Z2V0R2F0ZSgpe3N3aXRjaCh0aGlzLmdhdGVTdGF0ZSl7Y2FzZSJwcmV0cmlnIjpyZXR1cm4gdGhpcy5nYXRlU3RhdGU9Im9uIiwwO2Nhc2Uib24iOnJldHVybiAxO2Nhc2Uib2ZmIjpyZXR1cm4gMDtkZWZhdWx0OmcoITEpfX1nZXRGcmVxKCl7c3dpdGNoKHRoaXMuZ2F0ZVN0YXRlKXtjYXNlInByZXRyaWciOnJldHVybiB0aGlzLmdhdGVTdGF0ZT0ib24iLDA7Y2FzZSJvbiI6cmV0dXJuIHRoaXMuZnJlcTtjYXNlIm9mZiI6cmV0dXJuIHRoaXMuZnJlcTtkZWZhdWx0OmcoITEpfX1nZXRWZWxvY2l0eSgpe3N3aXRjaCh0aGlzLmdhdGVTdGF0ZSl7Y2FzZSJwcmV0cmlnIjpyZXR1cm4gdGhpcy5nYXRlU3RhdGU9Im9uIiwwO2Nhc2Uib24iOnJldHVybiB0aGlzLnZlbG9jaXR5O2Nhc2Uib2ZmIjpyZXR1cm4gdGhpcy52ZWxvY2l0eTtkZWZhdWx0OmcoITEpfX19Y2xhc3Mgb3QgZXh0ZW5kcyBte2NvbnN0cnVjdG9yKHQscyxlLGkpe3N1cGVyKHQscyxlLGkpLHRoaXMudHlwZT0ibWlkaWdhdGUifXVwZGF0ZSh0KXtyZXR1cm4gdGhpcy5jaGFubmVsPXQsdGhpcy5nZXRHYXRlKCl9fWNsYXNzIGN0IGV4dGVuZHMgbXtjb25zdHJ1Y3Rvcih0LHMsZSxpKXtzdXBlcih0LHMsZSxpKSx0aGlzLnR5cGU9Im1pZGlmcmVxIn11cGRhdGUodCl7cmV0dXJuIHRoaXMuY2hhbm5lbD10LHRoaXMuZ2V0RnJlcSgpfX1jbGFzcyBkdCBleHRlbmRzIG17Y29uc3RydWN0b3IodCxzLGUsaSl7c3VwZXIodCxzLGUsaSksdGhpcy50eXBlPSJtaWRpdmVsIn11cGRhdGUodCl7cmV0dXJuIHRoaXMuY2hhbm5lbD10LHRoaXMuZ2V0VmVsb2NpdHkoKX19Y2xhc3MgZnR7Y29uc3RydWN0b3IodCxzLGUsaSl7dGhpcy51cD0hMSx0aGlzLnNlbmQ9aSx0aGlzLnZhbHVlPTAsdGhpcy50eXBlPSJjYyJ9c2V0VmFsdWUodCl7dGhpcy52YWx1ZT10fXVwZGF0ZSh0LHMsZSl7cmV0dXJuIHRoaXMuaWQ9cywhdGhpcy51cCYmdD4wPyh0aGlzLnVwPSEwLHRoaXMuc2VuZCh7dHlwZToiU0lHTkFMX1RSSUdHRVIiLGlkOnMsdGltZTplfSksdGhpcy52YWx1ZSk6KHRoaXMudXA9dD4wLHRoaXMudmFsdWUpfX1jbGFzcyBwdCBleHRlbmRzIG97Y29uc3RydWN0b3IodCxzLGUsaSl7c3VwZXIodCxzLGUsaSksdGhpcy50eXBlPSJjYyIsdGhpcy52YWx1ZT1zLmlucHV0c1sxXT8/MH1zZXRWYWx1ZSh0KXt0aGlzLnZhbHVlPXR9dXBkYXRlKHQpe3JldHVybiB0aGlzLmlkPXQsdGhpcy52YWx1ZX19Y2xhc3MgYnQgZXh0ZW5kcyBve2NvbnN0cnVjdG9yKHQscyxlLGkpe3N1cGVyKHQscyxlLGkpLHRoaXMudHlwZT0ibWlkaWNjIix0aGlzLnZhbHVlPXMuaW5wdXRzWzJdPz8tMSx0aGlzLmNoYW5uZWw9LTEsdGhpcy5jY251bWJlcj0tMX1zZXRWYWx1ZSh0KXt0aGlzLnZhbHVlPXR9dXBkYXRlKHQscyl7cmV0dXJuIHRoaXMuY2NudW1iZXI9dCx0aGlzLmNoYW5uZWw9cyx0aGlzLnZhbHVlfX1jbGFzcyBndCBleHRlbmRzIG97Y29uc3RydWN0b3IodCxzLGUsaSl7c3VwZXIodCxzLGUsaSksdGhpcy5jbG9ja1Nnbj0hMCx0aGlzLnN0ZXA9MCx0aGlzLmZpcnN0PSEwfXVwZGF0ZSh0LC4uLnMpe3JldHVybiF0aGlzLmNsb2NrU2duJiZ0PjA/KHRoaXMuc3RlcD0odGhpcy5zdGVwKzEpJXMubGVuZ3RoLHRoaXMuY2xvY2tTZ249dD4wLDApOih0aGlzLmNsb2NrU2duPXQ+MCxzW3RoaXMuc3RlcF0pfX1jbGFzcyBtdCBleHRlbmRzIG97dXBkYXRlKHQsLi4ucyl7Y29uc3QgZT10JXMubGVuZ3RoK3MubGVuZ3RoO3JldHVybiBzW01hdGguZmxvb3IoZSklcy5sZW5ndGhdfX1jbGFzcyBTdHt1cGRhdGUodCxzLGUsaSxuKXtsZXQgcj1QKHQscyxlKTtyZXR1cm4gUyhyLGksbil9fWNsYXNzIHd0e3VwZGF0ZSh0LHMsZSl7cmV0dXJuIE1hdGgubWluKE1hdGgubWF4KHQscyksZSl9fWNsYXNzIHZ0e2NvbnN0cnVjdG9yKCl7dGhpcy5oaT0hMX11cGRhdGUodCl7cmV0dXJuIXRoaXMuaGkmJnQ+MD8odGhpcy5oaT0hMCwxKToodGhpcy5oaSYmdDw9MCYmKHRoaXMuaGk9ITEpLDApfX1jbGFzcyB5dHtjb25zdHJ1Y3Rvcigpe3RoaXMueDE9MCx0aGlzLngyPTAsdGhpcy55MT0wLHRoaXMueTI9MCx0aGlzLmEwPTEsdGhpcy5hMT0wLHRoaXMuYTI9MCx0aGlzLmIwPTEsdGhpcy5iMT0wLHRoaXMuYjI9MH11cGRhdGUodD0wLHM9MCxlPTUwMCxpPTEsbj0xKXtjb25zdCByPTIqTWF0aC5QSSplL3NhbXBsZVJhdGUsbD1NYXRoLnNpbihyKTtpPU1hdGgucG93KDEwLGkvMjApO2NvbnN0IHU9bC8oMippKSxjPU1hdGguY29zKHIpO2lmKHM9PT0wKXRoaXMuYjE9MS1jLHRoaXMuYjA9dGhpcy5iMS8yLHRoaXMuYjI9dGhpcy5iMCx0aGlzLmEwPTErdSx0aGlzLmExPS0yKmMsdGhpcy5hMj0xLXU7ZWxzZSBpZihzPT09MSl0aGlzLmIwPSgxK2MpLzIsdGhpcy5iMT0tKDErYyksdGhpcy5iMj10aGlzLmIwLHRoaXMuYTA9MSt1LHRoaXMuYTE9LTIqYyx0aGlzLmEyPTEtdTtlbHNlIGlmKHM9PT0yKXRoaXMuYjA9bC8yLHRoaXMuYjE9MCx0aGlzLmIyPS10aGlzLmIwLHRoaXMuYTA9MSt1LHRoaXMuYTE9LTIqYyx0aGlzLmEyPTEtdTtlbHNlIGlmKHM9PT0zKXRoaXMuYjA9MSx0aGlzLmIxPS0yKmMsdGhpcy5iMj0xLHRoaXMuYTA9MSt1LHRoaXMuYTE9LTIqYyx0aGlzLmEyPTEtdTtlbHNlIGlmKHM9PT00KXRoaXMuYjA9MS11LHRoaXMuYjE9LTIqYyx0aGlzLmIyPTErdSx0aGlzLmEwPTErdSx0aGlzLmExPS0yKmMsdGhpcy5hMj0xLXU7ZWxzZSBpZihzPT09NSl7Y29uc3QgYT1NYXRoLnBvdygxMCxuLzQwKTt0aGlzLmIwPTErdSphLHRoaXMuYjE9LTIqYyx0aGlzLmIyPTEtdSphLHRoaXMuYTA9MSt1L2EsdGhpcy5hMT0tMipjLHRoaXMuYTI9MS11L2F9ZWxzZSBpZihzPT09Nil7Y29uc3QgYT1NYXRoLnBvdygxMCxuLzQwKSxkPTIqTWF0aC5zcXJ0KGEpKnUsZj0oYS0xKSpjLHA9KGErMSkqYzt0aGlzLmIwPWEqKGErMS1mK2QpLHRoaXMuYjE9MiphKihhLTEtcCksdGhpcy5iMj1hKihhKzEtZi1kKSx0aGlzLmEwPWErMStmK2QsdGhpcy5hMT0tMiooYS0xK3ApLHRoaXMuYTI9YSsxK2YtZH1lbHNlIGlmKHM9PT03KXtjb25zdCBhPU1hdGgucG93KDEwLG4vNDApLGQ9MipNYXRoLnNxcnQoYSkqdSxmPShhLTEpKmMscD0oYSsxKSpjO3RoaXMuYjA9YSooYSsxK2YrZCksdGhpcy5iMT0tMiphKihhLTErcCksdGhpcy5iMj1hKihhKzErZi1kKSx0aGlzLmEwPWErMS1mK2QsdGhpcy5hMT0yKihhLTEtcCksdGhpcy5hMj1hKzEtZi1kfXRoaXMuYjAvPXRoaXMuYTAsdGhpcy5iMS89dGhpcy5hMCx0aGlzLmIyLz10aGlzLmEwLHRoaXMuYTEvPXRoaXMuYTAsdGhpcy5hMi89dGhpcy5hMCx0aGlzLmEwPTE7Y29uc3QgYj10aGlzLmIwKnQrdGhpcy5iMSp0aGlzLngxK3RoaXMuYjIqdGhpcy54Mi10aGlzLmExKnRoaXMueTEtdGhpcy5hMip0aGlzLnkyO3JldHVybiB0aGlzLngyPXRoaXMueDEsdGhpcy54MT10LHRoaXMueTI9dGhpcy55MSx0aGlzLnkxPWIsYn19Y29uc3QgTXQ9T2JqZWN0LmZyZWV6ZShPYmplY3QuZGVmaW5lUHJvcGVydHkoe19fcHJvdG9fXzpudWxsLEFEU1JOb2RlOnEsQXVkaW9JbjpsdCxBdWRpb05vZGU6byxCUEY6cnQsQmlxdWFkRmlsdGVyOnl0LEJyb3duTm9pc2VPc2M6VyxDQzpwdCxDTE9DS19QUFE6TSxDTE9DS19QUFM6TixDbGlwOnd0LENsb2NrOkYsQ2xvY2tEaXY6RCxDbG9ja091dDpMLERlbGF5OlYsRGlzdG9ydDpHLER1c3RPc2M6SyxGaWx0ZXI6bnQsRm9sZDp1dCxIb2xkOlIsSW1wdWxzZU9zYzpZLExhZzppdCxMY2dOb2lzZTpILE1pZGlDQzpidCxNaWRpRnJlcTpjdCxNaWRpR2F0ZTpvdCxNaWRpSW46bSxNaWRpVmVsOmR0LE5vaXNlT3NjOmosT3V0cHV0OkIsUGljazptdCxQaW5rTm9pc2U6WCxQdWxzZU9zYzp6LFJlbWFwOlN0LFNhd09zYzpKLFNjb3BlOmV0LFNlcXVlbmNlOmd0LFNpZGVjaGFpbkNvbXByZXNzb3I6dHQsU2lnbmFsOmZ0LFNpbmVPc2M6USxTbGV3Omh0LFNsaWRlOmF0LFRyaU9zYzpzdCxUcmlnOnZ0LFphd09zYzpafSxTeW1ib2wudG9TdHJpbmdUYWcse3ZhbHVlOiJNb2R1bGUifSkpLHg9bmV3IE1hcChPYmplY3QuZW50cmllcyhNdCkpO2NsYXNzIE90e2NvbnN0cnVjdG9yKHQscyl7Zyh0PT00OGUzKSx0aGlzLnNhbXBsZVJhdGU9dCx0aGlzLnBsYXlQb3M9MCx0aGlzLnNlbmQ9cyx0aGlzLnVuaXRzPVtdLHRoaXMudW5pdElEPTAsdGhpcy5mYWRlVGltZT0uMDEsdGhpcy5tYXhVbml0cz0xLHRoaXMucT1bXX1mYWRlT3V0VW5pdCh0KXt0LmZhZGVPdXQodGhpcy5wbGF5UG9zLHRoaXMuZmFkZVRpbWUpLHRoaXMuZnJlZVVuaXQodC5pZCx0aGlzLmZhZGVUaW1lKX1mYWRlT3V0VW5pdEJ5SWQodCl7Y29uc3Qgcz10aGlzLnVuaXRzLmZpbmQoZT0+ZS5pZD09PXQpO3MmJnRoaXMuZmFkZU91dFVuaXQocyl9ZmFkZU91dEFsbFVuaXRzKCl7dGhpcy51bml0cy5mb3JFYWNoKHQ9PnRoaXMuZmFkZU91dFVuaXQodCkpfWZhZGVPdXRPbGRVbml0cygpe2NvbnN0IHQ9dGhpcy51bml0cy5maWx0ZXIoZT0+ZS5hY3RpdmUpLHM9dC5sZW5ndGgtdGhpcy5tYXhVbml0cztzPD0wfHx0LnNsaWNlKDAscykuZm9yRWFjaChlPT50aGlzLmZhZGVPdXRVbml0KGUpKX1zdG9wKCl7dGhpcy5mYWRlT3V0QWxsVW5pdHMoKSx0aGlzLnNlbmQoe3R5cGU6IlNUT1AiLGZhZGVUaW1lOnRoaXMuZmFkZVRpbWV9KX1zcGF3blVuaXQodCxzKXtjb25zdCBlPW5ldyB4dCh0aGlzLnVuaXRJRCsrLHQsdGhpcy5zYW1wbGVSYXRlLHRoaXMuc2VuZCk7dGhpcy51bml0cy5wdXNoKGUpLGUuZmFkZUluKHRoaXMucGxheVBvcyx0aGlzLmZhZGVUaW1lKSx0aGlzLmZhZGVPdXRPbGRVbml0cygpLGNvbnNvbGUubG9nKGBzcGF3biB1bml0ICR7ZS5pZH0sIHVuaXRzIGFsaXZlOiAke3RoaXMudW5pdHMubGVuZ3RofWApLHMmJnRoaXMuc2NoZWR1bGVNZXNzYWdlKHttc2c6e3R5cGU6IkZBREVfT1VUX1VOSVQiLGlkOmUuaWR9LHRpbWU6c30pfWZyZWVVbml0KHQscyl7aWYocyl7dGhpcy5zY2hlZHVsZU1lc3NhZ2Uoe21zZzp7dHlwZToiRlJFRV9VTklUIixpZDp0fSx0aW1lOnN9KTtyZXR1cm59Y29uc3QgZT10aGlzLnVuaXRzLmxlbmd0aDt0aGlzLnVuaXRzPXRoaXMudW5pdHMuZmlsdGVyKGk9PmkuaWQhPT10KSxlPnRoaXMudW5pdHMubGVuZ3RoJiZjb25zb2xlLmxvZyhgZnJlZSB1bml0ICR7dH0sIHVuaXRzIGFsaXZlOiAke3RoaXMudW5pdHMubGVuZ3RofWApfXBhcnNlTXNnKHQpe3N3aXRjaCh0LnR5cGUpe2Nhc2UiU1BBV05fVU5JVCI6dGhpcy5zcGF3blVuaXQodC51bml0LHQuZHVyYXRpb24pO2JyZWFrO2Nhc2UiRlJFRV9VTklUIjp0aGlzLmZyZWVVbml0KHQuaWQpO2JyZWFrO2Nhc2UiRkFERV9PVVRfVU5JVCI6dGhpcy5mYWRlT3V0VW5pdEJ5SWQodC5pZCk7YnJlYWs7Y2FzZSJOT1RFX09OIjp0aGlzLm5vdGVPbih0KTticmVhaztjYXNlIkNDIjp0aGlzLm1pZGlDQyh0KTticmVhaztjYXNlIlNFVF9DT05UUk9MIjp0aGlzLnNldENvbnRyb2wodCk7YnJlYWs7Y2FzZSJGQURFX1RJTUUiOnRoaXMuZmFkZVRpbWU9TnVtYmVyKHQuZmFkZVRpbWUpO2JyZWFrO2Nhc2UiTUFYX1VOSVRTIjp0aGlzLm1heFVuaXRzPU51bWJlcih0Lm1heFVuaXRzKTticmVhaztjYXNlIlNUT1AiOnRoaXMuc3RvcCgpO2JyZWFrO2Nhc2UiU0VUX1VHRU4iOnRoaXMuYWRkVWdlbih0LmNsYXNzTmFtZSx0LnVnZW4pO2JyZWFrO2Nhc2UiU0NIRURVTEVfTVNHIjp0aGlzLnNjaGVkdWxlTWVzc2FnZSh0KTticmVhaztjYXNlIkJBVENIX01TRyI6dC5tZXNzYWdlcy5mb3JFYWNoKHM9PnRoaXMucGFyc2VNc2cocykpO2JyZWFrO2RlZmF1bHQ6dGhyb3cgbmV3IFR5cGVFcnJvcihgdW5rbm93biBtZXNzYWdlIHR5cGUgJHt0LnR5cGV9YCl9fW5vdGVPbih0KXt0aGlzLnVuaXRzLmZvckVhY2gocz0+cy5ub3RlT24odCkpfW1pZGlDQyh0KXt0aGlzLnVuaXRzLmZvckVhY2gocz0+cy5taWRpQ0ModCkpfXNldENvbnRyb2wodCl7dGhpcy51bml0cy5mb3JFYWNoKHM9PnMuc2V0Q29udHJvbCh0KSl9c2NoZWR1bGVNZXNzYWdlKHQpe2lmKHQudGltZT10aGlzLnBsYXlQb3MrdC50aW1lLCF0aGlzLnEubGVuZ3RoKXt0aGlzLnEucHVzaCh0KTtyZXR1cm59bGV0IHM9MDtmb3IoO3M8dGhpcy5xLmxlbmd0aCYmdGhpcy5xW3NdLnRpbWU8dC50aW1lOylzKys7dGhpcy5xLnNwbGljZShzLDAsdCl9Z2VuU2FtcGxlKHQpe2Zvcig7dGhpcy5xLmxlbmd0aD4wJiZ0aGlzLnFbMF0udGltZTw9dGhpcy5wbGF5UG9zOyl0aGlzLnBhcnNlTXNnKHRoaXMucVswXS5tc2cpLHRoaXMucS5zaGlmdCgpO2lmKCF0aGlzLnVuaXRzLmxlbmd0aClyZXR1cm5bMCwwXTtjb25zdCBzPVswLDBdO2ZvcihsZXQgZT0wO2U8dGhpcy51bml0cy5sZW5ndGg7ZSsrKXtjb25zdCBpPXRoaXMudW5pdHNbZV0sbj1pLmdldExldmVsKHRoaXMucGxheVBvcyk7aS5nZW5TYW1wbGUodGhpcy5wbGF5UG9zLGkubm9kZXMsdCxpLnJlZ2lzdGVycyxpLm91dHB1dHMsaS5zb3VyY2VzKSxzWzBdKz1pLm91dHB1dHNbMF0qbixzWzFdKz1pLm91dHB1dHNbMV0qbn1yZXR1cm4gdGhpcy5wbGF5UG9zKz0xLzQ4ZTMsc31hZGRVZ2VuKHQscyl7Y29uc3QgZT1uZXcgRnVuY3Rpb24oYCR7c307cmV0dXJuICR7dH1gKSgpO3guc2V0KHQsZSl9fWNsYXNzIHh0e2NvbnN0cnVjdG9yKHQscyxlLGkpe3RoaXMuaWQ9dCx0aGlzLnNhbXBsZVJhdGU9ZSx0aGlzLnNlbmQ9aSx0aGlzLm5vZGVzPVtdLHRoaXMuYWN0aXZlPSEwO2ZvcihsZXQgciBpbiBzLnVnZW5zKXtjb25zdCBsPXMudWdlbnNbcl07aWYoeC5oYXMobC50eXBlKSl7Y29uc3QgdT14LmdldChsLnR5cGUpLGM9TnVtYmVyKHIpO3RoaXMubm9kZXNbY109bmV3IHUoYyxsLHRoaXMuc2FtcGxlUmF0ZSx0aGlzLnNlbmQpfWVsc2UgY29uc29sZS53YXJuKGB1bmtub3duIHVnZW4gIiR7bC50eXBlfSJgKX10aGlzLnJlZ2lzdGVycz1uZXcgQXJyYXkocy5yZWdpc3RlcnMpLmZpbGwoMCk7bGV0IG49MTY7dGhpcy5vdXRwdXRzPW5ldyBBcnJheShuKS5maWxsKDApLHRoaXMuc291cmNlcz1uZXcgQXJyYXkobikuZmlsbCgwKSxzLnNyYz1gby5maWxsKDApOyAvLyByZXNldCBvdXRwdXRzCmArcy5zcmMsdGhpcy5nZW5TYW1wbGU9bmV3IEZ1bmN0aW9uKCJ0aW1lIiwibm9kZXMiLCJpbnB1dCIsInIiLCJvIiwicyIscy5zcmMpfW5vdGVPbih0KXt2YXIgdSxjLGI7Y29uc3R7Y2hhbm5lbDpzLG5vdGU6ZSx2ZWxvY2l0eTppfT10LG49dGhpcy5ub2Rlcy5maWx0ZXIoYT0+YS50eXBlPT09Im1pZGlmcmVxIiYmKGEuY2hhbm5lbD09PS0xfHxhLmNoYW5uZWw9PT1zKSkscj10aGlzLm5vZGVzLmZpbHRlcihhPT5hLnR5cGU9PT0ibWlkaWdhdGUiJiYoYS5jaGFubmVsPT09LTF8fGEuY2hhbm5lbD09PXMpKSxsPXRoaXMubm9kZXMuZmlsdGVyKGE9PmEudHlwZT09PSJtaWRpdmVsIiYmKGEuY2hhbm5lbD09PS0xfHxhLmNoYW5uZWw9PT1zKSk7aWYoaT4wKXtsZXQgYT1uLmZpbmQocD0+cC5pc0ZyZWUoKSl8fG5bMF0sZD1yLmZpbmQocD0+cC5pc0ZyZWUoKSl8fHJbMF0sZj1sLmZpbmQocD0+cC5pc0ZyZWUoKSl8fGxbMF07YT09bnVsbHx8YS5ub3RlT24oZSxpKSxkPT1udWxsfHxkLm5vdGVPbihlLGkpLGY9PW51bGx8fGYubm90ZU9uKGUsaSl9ZWxzZSh1PW4uZmluZChhPT5hLm5vdGU9PT1lKSk9PW51bGx8fHUubm90ZU9mZigpLChjPXIuZmluZChhPT5hLm5vdGU9PT1lKSk9PW51bGx8fGMubm90ZU9mZigpLChiPWwuZmluZChhPT5hLm5vdGU9PT1lKSk9PW51bGx8fGIubm90ZU9mZigpfW1pZGlDQyh0KXtjb25zdHtjaGFubmVsOnMsY2M6ZSx2YWx1ZTppfT10O3RoaXMubm9kZXMuZm9yRWFjaChuPT57bi50eXBlPT09Im1pZGljYyImJihuLmNoYW5uZWw9PT0tMXx8bi5jaGFubmVsPT09cykmJm4uY2NudW1iZXI9PT1lJiZuLnNldFZhbHVlKGkpfSl9c2V0Q29udHJvbCh0KXtjb25zdHt2YWx1ZTpzLGlkOmV9PXQsaT10aGlzLm5vZGVzLmZpbmQobj0+bi50eXBlPT09ImNjIiYmbi5pZD09PWUpO2kmJmkuc2V0VmFsdWUocyl9Z2V0TGV2ZWwodCl7cmV0dXJuIHRoaXMuZmFkZVN0YXJ0PT09dm9pZCAwPzA6dGhpcy5hY3RpdmU/UygodC10aGlzLmZhZGVTdGFydCkvdGhpcy5mYWRlVGltZSwwLC4zKTpTKCh0LXRoaXMuZmFkZVN0YXJ0KS90aGlzLmZhZGVUaW1lLHRoaXMuZmFkZUZyb20sMCl9ZmFkZUluKHQscyl7dGhpcy5mYWRlU3RhcnQ9dCx0aGlzLmZhZGVUaW1lPXN9ZmFkZU91dCh0LHMpe3RoaXMuZmFkZVRpbWU9cyx0aGlzLmZhZGVGcm9tPXRoaXMuZ2V0TGV2ZWwodCksdGhpcy5hY3RpdmU9ITEsdGhpcy5mYWRlU3RhcnQ9dH1pc0RvbmUodCl7cmV0dXJuIXRoaXMuYWN0aXZlJiZ0aGlzLmdldExldmVsKHQpPT09MH19Y2xhc3MgVHQgZXh0ZW5kcyBBdWRpb1dvcmtsZXRQcm9jZXNzb3J7Y29uc3RydWN0b3IoKXtzdXBlcigpLHRoaXMucG9ydC5vbm1lc3NhZ2U9dGhpcy5vbm1lc3NhZ2UuYmluZCh0aGlzKSx0aGlzLmF1ZGlvR3JhcGg9bmV3IE90KDQ4ZTMsdGhpcy5wb3J0LnBvc3RNZXNzYWdlLmJpbmQodGhpcy5wb3J0KSl9b25tZXNzYWdlKHQpe2xldCBzPXQuZGF0YTt0aGlzLmF1ZGlvR3JhcGgucGFyc2VNc2cocyl9cHJvY2Vzcyh0LHMsZSl7Y29uc3QgaT1zWzBdLG49dFswXVswXSxyPWlbMF0sbD1pWzFdO2ZvcihsZXQgdT0wO3U8ci5sZW5ndGg7dSsrKXtsZXRbYyxiXT10aGlzLmF1ZGlvR3JhcGguZ2VuU2FtcGxlKG4/blt1XTowKTtyW3VdPWMsbFt1XT1ifXJldHVybiEwfX1yZWdpc3RlclByb2Nlc3Nvcigic2FtcGxlLWdlbmVyYXRvciIsVHQpfSkoKTsK", qt2 = "data:text/javascript;base64,KGZ1bmN0aW9uKCl7InVzZSBzdHJpY3QiO2NsYXNzIG4gZXh0ZW5kcyBBdWRpb1dvcmtsZXRQcm9jZXNzb3J7c3RhdGljIGdldCBwYXJhbWV0ZXJEZXNjcmlwdG9ycygpe3JldHVyblt7bmFtZToiaXNSZWNvcmRpbmciLGRlZmF1bHRWYWx1ZTowfV19Y29uc3RydWN0b3IoKXtzdXBlcigpLHRoaXMuX2J1ZmZlclNpemU9MjA0OCx0aGlzLl9idWZmZXI9bmV3IEZsb2F0MzJBcnJheSh0aGlzLl9idWZmZXJTaXplKSx0aGlzLl9pbml0QnVmZmVyKCl9X2luaXRCdWZmZXIoKXt0aGlzLl9ieXRlc1dyaXR0ZW49MH1faXNCdWZmZXJFbXB0eSgpe3JldHVybiB0aGlzLl9ieXRlc1dyaXR0ZW49PT0wfV9pc0J1ZmZlckZ1bGwoKXtyZXR1cm4gdGhpcy5fYnl0ZXNXcml0dGVuPT09dGhpcy5fYnVmZmVyU2l6ZX1fYXBwZW5kVG9CdWZmZXIoZSl7dGhpcy5faXNCdWZmZXJGdWxsKCkmJnRoaXMuX2ZsdXNoKCksdGhpcy5fYnVmZmVyW3RoaXMuX2J5dGVzV3JpdHRlbl09ZSx0aGlzLl9ieXRlc1dyaXR0ZW4rPTF9X2ZsdXNoKCl7bGV0IGU9dGhpcy5fYnVmZmVyO3RoaXMuX2J5dGVzV3JpdHRlbjx0aGlzLl9idWZmZXJTaXplJiYoZT1lLnNsaWNlKDAsdGhpcy5fYnl0ZXNXcml0dGVuKSksdGhpcy5wb3J0LnBvc3RNZXNzYWdlKHtldmVudFR5cGU6ImRhdGEiLGF1ZGlvQnVmZmVyOmV9KSx0aGlzLl9pbml0QnVmZmVyKCl9X3JlY29yZGluZ1N0b3BwZWQoKXt0aGlzLnBvcnQucG9zdE1lc3NhZ2Uoe2V2ZW50VHlwZToic3RvcCJ9KX1wcm9jZXNzKGUsbyxoKXtjb25zdCBpPWguaXNSZWNvcmRpbmcsZj1vWzBdLHM9ZVswXSx1PWZbMF0sXz1mWzFdO2xldCByPSExO2ZvcihsZXQgdD0wO3Q8dS5sZW5ndGg7dCsrKXQ8aS5sZW5ndGgmJihyPWlbdF09PT0xKSwhciYmIXRoaXMuX2lzQnVmZmVyRW1wdHkoKSYmKHRoaXMuX2ZsdXNoKCksdGhpcy5fcmVjb3JkaW5nU3RvcHBlZCgpKSxyJiYodGhpcy5fYXBwZW5kVG9CdWZmZXIoc1swXVt0XSksdGhpcy5fYXBwZW5kVG9CdWZmZXIoc1sxXVt0XSkpLHVbdF09c1swXVt0XSxfW3RdPXNbMV1bdF07cmV0dXJuITB9fXJlZ2lzdGVyUHJvY2Vzc29yKCJyZWNvcmRlciIsbil9KSgpOwo=";
      function _t2(e, t, i) {
        if (e.length < 1) return;
        e[0];
        const n = 3, s = 32, d2 = e.map((Z2) => Z2.length).reduce((Z2, w2) => Z2 + w2, 0), c2 = s / 8, f2 = i * c2, p = 44, h = new ArrayBuffer(p + d2 * c2), G2 = new DataView(h);
        Y2(G2, 0, "RIFF"), G2.setUint32(4, 36 + d2 * c2, true), Y2(G2, 8, "WAVE"), Y2(G2, 12, "fmt "), G2.setUint32(16, 16, true), G2.setUint16(20, n, true), G2.setUint16(22, i, true), G2.setUint32(24, t, true), G2.setUint32(28, t * f2, true), G2.setUint16(32, f2, true), G2.setUint16(34, s, true), Y2(G2, 36, "data"), G2.setUint32(40, d2 * c2, true);
        let z2 = 44;
        for (const Z2 of e) ei2(G2, z2, Z2), z2 += Z2.length * c2;
        return h;
      }
      function Y2(e, t, i) {
        for (let n = 0; n < i.length; n++) e.setUint8(t + n, i.charCodeAt(n));
      }
      function ei2(e, t, i) {
        for (var n = 0; n < i.length; n++, t += 4) e.setFloat32(t, i[n], true);
      }
      const ie2 = Object.freeze(Object.defineProperty({ __proto__: null, Node: u, compile: W2, evaluate: v, exit: C2, exportModule: _, getInletName: q2, getNode: K2, module: g, n: X, node: R2, nodeRegistry: r, outputType: V2, polyType: b, register: m2, registerNode: o }, Symbol.toStringTag, { value: "Module" }));
      let ti2 = (e) => `Math.sin(${e})`, ii2 = (e) => `Math.cos(${e})`, ni2 = (e) => `Math.tan(${e})`, li2 = (e) => `Math.asin(${e})`, ai2 = (e) => `Math.acos(${e})`, si2 = (e) => `Math.atan(${e})`, ne2 = (e, t, i) => `${e} = ${t};${i ? ` /* ${i} */` : ""}`, U2 = (e, ...t) => ne2(e.name, `nodes[${e.ugenIndex}].update(${t.join(",")})`, e.node.type), oi2 = (e) => `(2 ** ((${e} - 69) / 12) * 440)`, di2 = (e, t) => `${e} ** ${t}`, ci2 = (e) => `Math.exp(${e})`, ui2 = (e) => `Math.log(${e})`, pi2 = (e, t) => `${e}%${t}`, mi2 = (e) => `Math.abs(${e})`, ri2 = (e) => `Math.round(${e})`, hi2 = (e) => `Math.floor(${e})`, Gi2 = (e) => `Math.sign(${e})`, yi2 = (e) => `Math.ceil(${e})`, fi2 = (e, t) => `Math.min(${e}, ${t})`, gi2 = (e, t) => `Math.max(${e}, ${t})`, Xi2 = (e, t) => `[${e}, ${t}]`, L2 = (e) => `${e}[0]`;
      const Zi2 = Object.freeze(Object.defineProperty({ __proto__: null, abs: mi2, ceil: yi2, def: ne2, defAcos: ai2, defAsin: li2, defAtan: si2, defCos: ii2, defSin: ti2, defTan: ni2, defUgen: U2, exp: ci2, floor: hi2, log: ui2, max: gi2, midinote: oi2, min: fi2, mod: pi2, pair_a: L2, pair_a_max: (e, t) => `(${L2(e)} > ${L2(t)} ? ${e} : ${t})`, pair_a_min: (e, t) => `(${L2(e)} < ${L2(t)} ? ${e} : ${t})`, pair_b: (e) => `${e}[1]`, pair_make: Xi2, pow: di2, round: ri2, sign: Gi2 }, Symbol.toStringTag, { value: "Module" }));
      class le2 {
        constructor(t = null) {
          this.ugens = /* @__PURE__ */ new Map(), this.outputNode = t;
        }
        async spawn(t, i) {
          this.graph = t;
          const { src: n, ugens: s, registers: d2 } = t.compile({ log: false });
          !this.mouse && n.includes("mouse") && this.initMouse(), !this.midiInited && s.some((c2) => c2.type.startsWith("Midi")) && this.initMidi(), !this.audioIn && s.some((c2) => c2.type === "AudioIn") && await this.initAudioIn(), this.sendCustomUgens(), this.send({ type: "SPAWN_UNIT", unit: { src: n, ugens: s, registers: d2 }, duration: i });
        }
        registerUgen(t) {
          this.ugens.set(t.name, t);
        }
        sendCustomUgens() {
          if (!this.ugens.size) return;
          let t = [];
          for (let [i, n] of this.ugens) t.push({ type: "SET_UGEN", className: i, ugen: n + "" });
          this.send({ type: "BATCH_MSG", messages: t });
        }
        scheduleMessage(t, i) {
          this.send({ type: "SCHEDULE_MSG", msg: t, time: i });
        }
        setControl(t, i, n) {
          const s = { type: "SET_CONTROL", id: t, value: i };
          n ? this.send({ type: "SCHEDULE_MSG", time: n, msg: s }) : this.send(s);
        }
        setControls(t) {
          const i = { type: "BATCH_MSG", messages: t.map((n) => {
            const s = { type: "SET_CONTROL", id: n.id, value: n.value };
            return n.time === void 0 ? s : { type: "SCHEDULE_MSG", time: n.time, msg: s };
          }) };
          this.send(i);
        }
        async initAudioIn() {
          console.log("init audio input...");
          const t = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
          this.audioCtx.createMediaStreamSource(t).connect(this.audioWorklet);
        }
        initMidi() {
          console.log("init midi input..."), this.midiInited = true, new Ot2().on("midimessage", (i, n) => {
            const s = $t2(n);
            s && this.send(s);
          });
        }
        initMouse() {
          console.log("init mouse"), this.mouse = new At(), this.mouse.on("move", (t, i) => {
            this.setControl("mouseX", t), this.setControl("mouseY", i);
          });
        }
        send(t) {
          T(t instanceof Object), this.audioWorklet && this.audioWorklet.port.postMessage(t);
        }
        async init() {
          if (!this.audioCtx) {
            if (T(!this.audioCtx), this.audioCtx = this.outputNode?.context || new AudioContext({ latencyHint: "interactive", sampleRate: 48e3 }), await this.audioCtx.resume(), !this.audioCtx.audioWorklet) throw new Error("Audio cannot be loaded: non-secure origin? (AudioContext.audioWorklet is undefined)");
            await this.audioCtx.audioWorklet.addModule(Dt), await this.audioCtx.audioWorklet.addModule(qt2), this.audioWorklet = new AudioWorkletNode(this.audioCtx, "sample-generator", { outputChannelCount: [2] }), this.audioWorklet.port.onmessage = (t) => {
              const { id: i, time: n, type: s } = t.data;
              s === "SIGNAL_TRIGGER" ? this.graph.dfs((d2) => {
                if (d2.type === "signal" && d2.id === i) {
                  const c2 = d2.callback(n, i);
                  isNaN(c2) ? c2 !== void 0 && console.warn(`expected number from "on" callback with id "${i}", got "${c2}" instead.`) : window.postMessage({ type: "KABELSALAT_SET_CONTROL", value: c2, id: i });
                }
                return d2;
              }) : s === "STOP" ? setTimeout(() => this.destroy(), t.data.fadeTime * 1e3 + 200) : s === "SEND_SAMPLES" && this.graph.dfs((d2) => (d2.type !== "scope" || d2.ins.length < 2 || d2.ins[1].value !== i || window.postMessage({ type: "KABELSALAT_UPDATE_SCOPE", samples: t.data.samples, channels: t.data.channels, channel: t.data.channel, id: i }), d2));
            }, this.recorder = new window.AudioWorkletNode(this.audioCtx, "recorder"), this.audioWorklet.connect(this.recorder), this.sendCustomUgens(), this.recorder.connect(this.outputNode || this.audioCtx.destination), this.recorder.port.onmessage = (t) => {
              if (t.data.eventType === "data" && this.recordedBuffers.push(t.data.audioBuffer), t.data.eventType === "stop") {
                console.log("recording stopped");
                const i = _t2(this.recordedBuffers, this.audioCtx.sampleRate, 2);
                bi2(i, "kabelsalat.wav", "audio/wav"), this.recordedBuffers = [];
              }
            }, this.recordOnPlay && this.record();
          }
        }
        destroy() {
          this.audioWorklet?.disconnect(), this.audioWorklet = null, this.recorder?.disconnect(), this.recorder = null, !this.outputNode && this.audioCtx?.close(), this.audioCtx = null;
        }
        stop() {
          this.audioCtx && this.send({ type: "STOP" }), this.mouse?.detach();
        }
        record() {
          if (!this.audioCtx) {
            this.recordOnPlay = true;
            return;
          }
          this.recordedBuffers = [], this.recorder.parameters.get("isRecording").setValueAtTime(1, 0), console.log("recording started");
        }
        stopRecording() {
          this.recordOnPlay = false, this.audioCtx && this.recorder.parameters.get("isRecording").setValueAtTime(0, 0);
        }
        set fadeTime(t) {
          this.send({ type: "FADE_TIME", fadeTime: t });
        }
        set maxUnits(t) {
          this.send({ type: "MAX_UNITS", maxUnits: t });
        }
      }
      function bi2(e, t, i) {
        const n = new Blob([e], { type: i }), s = document.createElement("a");
        s.href = window.URL.createObjectURL(n), s.download = t, s.click();
      }
      let Ri2 = 0, Mi2 = m2("signal", (e, t) => {
        const i = Ri2++, n = getNode("signal", e, i);
        return n.callback = t, n.id = i, n;
      }, { ugen: "Signal", compile: ({ vars: [e, t], ...i }) => U2(i, e, t, "time") }), Li2 = (e) => `sin(${e})`, xi2 = (e) => `cos(${e})`, zi2 = (e) => `tan(${e})`, Vi2 = (e) => `asin(${e})`, Wi2 = (e) => `acos(${e})`, Yi2 = (e) => `atan(${e})`, k = (e, t, i) => `${e} = ${t};${i ? ` /* ${i} */` : ""}`, Ni2 = (e, ...t) => {
        if (t.unshift(`nodes[${e.ugenIndex}]`), e.ugen === "Sequence" || e.ugen === "Pick") {
          const i = t.length - 2, n = `(float[${i}]){${t.slice(2).join(",")}}`;
          return k(e.name, `${e.ugen}_update(${t[0]}, ${t[1]}, ${i}, ${n})`, e.ugen);
        }
        return k(e.name, `${e.ugen}_update(${t.join(",")})`, e.ugen);
      }, Hi2 = (e) => `pow(2.0, ((${e} - 69.0) / 12.0)) * 440.0`, Si2 = (e, t) => `pow(${e}, ${t})`, wi2 = (e) => `exp(${e})`, Ti2 = (e) => `log(${e})`, Ki2 = (e, t) => `${e}>=${t}?${e}-${t}:${e}`, Ci2 = (e) => `fabs(${e})`, vi2 = (e, t) => `fmin(${e}, ${t})`, Ii2 = (e, t) => `fmax(${e}, ${t})`, Ui2 = (e) => `fround(${e})`, ki2 = (e) => `floor(${e})`, Pi2 = (e) => `ceil(${e})`, Fi2 = (e, t) => `((pair) {${e}, ${t}})`, x = (e) => `${e}.a`;
      const a = { js: Zi2, c: Object.freeze(Object.defineProperty({ __proto__: null, abs: Ci2, ceil: Pi2, def: k, defAcos: Wi2, defAsin: Vi2, defAtan: Yi2, defCos: xi2, defSin: Li2, defTan: zi2, defUgen: Ni2, exp: wi2, floor: ki2, log: Ti2, max: Ii2, midinote: Hi2, min: vi2, mod: Ki2, pair_a: x, pair_a_max: (e, t) => `(${x(e)} > ${x(t)} ? ${e} : ${t})`, pair_a_min: (e, t) => `(${x(e)} < ${x(t)} ? ${e} : ${t})`, pair_b: (e) => `${e}.b`, pair_make: Fi2, pow: Si2, round: Ui2 }, Symbol.toStringTag, { value: "Module" })) }, P2 = (e, t) => o(e, { ugen: t, compile: ({ vars: i, ...n }) => a[n.lang].defUgen(n, ...i) });
      let ae2 = m2("time", (e) => new u("time", e), { tags: ["meta"], description: "Returns elapsed time in seconds", compile: ({ name: e, lang: t }) => a[t].def(e, "time") }), se2 = m2("raw", (e, t) => new u("raw", t).withIns(X(e)), { ins: [{ name: "in" }, { name: "code", description: "expression with variable `t` being the elapsed time and `$input` the input." }], tags: ["meta"], description: "Raw code node, expects floats between -1 and 1", compile: ({ vars: e, node: t, name: i }) => `let $input = ${e[0]}; 
const ${i} = (${t.value}); // raw`, examples: [`sine(4).range(.5,1)
.raw("(time*110%1*2-1)*$input")
.out()`] }), oe2 = m2("bytebeat", (e, t) => new u("bytebeat", t).withIns(X(e)), { ins: [{ name: "t", description: "time in samples" }, { name: "code", description: "bytebeat code with variable `t`" }], tags: ["meta"], description: "Bytebeat node, expects numbers from 0 to 255", examples: [`time().mul(8000).bytebeat\`
// Fractalized Past
// by: lhphr
// from: https://dollchan.net/btb/res/3.html#69

(t>>10^t>>11)%5*((t>>14&3^t>>15&1)+1)*t%99+((3+(t>>14&3)-(t>>16&1))/3*t%99&64)
\`.out()`], compile: ({ vars: e, node: t, name: i }) => `let t = ${e[0]}; 
const ${i} = ((${t.value}) & 255) / 127.5 - 1; // bytebeat` }), de2 = m2("floatbeat", (e, t) => new u("bytebeat", t).withIns(X(e)), { ins: [{ name: "t", description: "time in samples" }, { name: "code", description: "floatbeat code with variable `t`" }], tags: ["meta"], description: "Raw code node, expects numbers from -1 to 1", compile: ({ vars: e, node: t, name: i }) => `let t = ${e[0]}; const ${i} = (${t.value}); // floatbeat` }), ce2 = o("adsr", { ugen: "ADSRNode", tags: ["envelope"], description: "ADSR envelope", examples: [`impulse(1).perc(.5)
.adsr(.01, .1, .5, .1)
.mul(sine(220)).out()`], ins: [{ name: "gate", default: 0, description: "gate input" }, { name: "att", default: 0.02, description: "attack time" }, { name: "dec", default: 0.1, description: "decay time" }, { name: "sus", default: 0.2, description: "sustain level" }, { name: "rel", default: 0.1, description: "release time" }], compile: ({ vars: [e = 0, t = 0.02, i = 0.1, n = 0.2, s = 0.1], ...d2 }) => a[d2.lang].defUgen(d2, "time", e, t, i, n, s) }), ue2 = g("ar", (e = 0, t = 0.02, i = 0.1) => e.adsr(t, 0, 1, i), { tags: ["envelope"], description: "AR envelope", examples: ["impulse(1).ad(.01, .1).mul(sine(220)).out()"], ins: [{ name: "trig", default: 0, description: "gate input" }, { name: "att", default: 0.02, description: "attack time" }, { name: "rel", default: 0.1, description: "release time" }] }), pe2 = g("ad", (e = 0, t = 0.02, i = 0.1) => e.adsr(t, i, 0, i), { tags: ["envelope"], description: "AD envelope", examples: ["impulse(1).ad(.01, .1).mul(sine(220)).out()"], ins: [{ name: "trig", default: 0, description: "gate input" }, { name: "att", default: 0.02, description: "attack time" }, { name: "dec", default: 0.1, description: "decay time" }] }), me2 = o("clock", { ugen: "Clock", internal: true, tags: ["regular", "clock"], description: "Clock source, with tempo in BPM", examples: ["clock(120).clockdiv(16).mul(sine(220)).out()"], ins: [{ name: "bpm", default: 120, description: "clock tempo in bpm (beats per minute)" }], compile: ({ vars: [e = 120], ...t }) => a[t.lang].defUgen(t, e) }), re2 = o("clockdiv", { ugen: "ClockDiv", tags: ["clock", "trigger"], description: "Clock signal divider", examples: ["impulse(8).clockdiv(2).ad(.1,.1).mul(sine(220)).out()"], ins: [{ name: "clock", default: 0, description: "clock input" }, { name: "divisor", default: 2, description: "tempo divisor" }], compile: ({ vars: [e = 0, t = 2], ...i }) => a[i.lang].defUgen(i, e, t) }), he2 = o("distort", { ugen: "Distort", tags: ["fx", "distortion"], description: "Overdrive-style distortion", examples: [`sine(220)
.distort( saw(.5).range(0,1) )
.out()`], ins: [{ name: "in", default: 0 }, { name: "amt", default: 0, description: "distortion amount" }], compile: ({ vars: [e = 0, t = 0], ...i }) => a[i.lang].defUgen(i, e, t) }), F2 = o("noise", { ugen: "NoiseOsc", tags: ["source", "noise"], description: "White noise source", examples: ["noise().mul(.25).out()"], ins: [{ name: "next", default: 1, description: "if 0, the noise will hold the previous value. defaults to 1." }], compile: ({ lang: e, vars: [t = 1], ...i }) => a[e].defUgen(i, t) }), Ge2 = o("lcgnoise", { ugen: "LcgNoise", tags: ["source", "noise"], description: "Lcg white noise source.", examples: ["lcgnoise().mul(.25).out()"], ins: [{ name: "next", default: 1, description: "if 0, the noise will hold the previous value. defaults to 1." }, { name: "reset", default: 0, description: "if 1, the random number generator sequence will reset." }], compile: ({ lang: e, vars: [t = 1, i = 0], ...n }) => a[e].defUgen(n, t, i) }), ye2 = o("pink", { ugen: "PinkNoise", tags: ["source", "noise"], description: "Pink noise source", examples: ["pink().mul(.5).out()"], ins: [], compile: ({ lang: e, ...t }) => a[e].defUgen(t) }), fe2 = o("brown", { ugen: "BrownNoiseOsc", tags: ["source", "noise"], description: "Brown noise source", examples: ["brown().out()"], ins: [], compile: ({ lang: e, ...t }) => a[e].defUgen(t) }), ge2 = o("dust", { ugen: "DustOsc", tags: ["trigger", "noise", "source"], description: "Generates random impulses from 0 to +1.", examples: ["dust(200).out()"], ins: [{ name: "density", default: 0, description: "average impulses per second" }], compile: ({ vars: [e = 0], ...t }) => a[t.lang].defUgen(t, e) }), J2 = o("impulse", { ugen: "ImpulseOsc", tags: ["regular", "trigger"], description: "Regular single sample impulses (0 - 1)", examples: ["impulse(10).out()"], ins: [{ name: "freq", default: 0 }, { name: "phase", default: 0 }], compile: ({ vars: [e = 0, t = 0], ...i }) => a[i.lang].defUgen(i, e, t) }), Xe2 = o("saw", { ugen: "SawOsc", tags: ["regular", "waveform", "source"], description: "Sawtooth wave oscillator with anti aliasing", examples: ["saw(110).mul(.5).out()"], ins: [{ name: "freq", default: 0 }], compile: ({ vars: [e = 0], ...t }) => a[t.lang].defUgen(t, e) }), Ze2 = o("zaw", { ugen: "ZawOsc", tags: ["regular", "waveform", "source"], description: "Sawtooth wave oscillator with sharp edges. Use saw for anti aliased variant.", examples: ["zaw(110).mul(.5).out()"], ins: [{ name: "freq", default: 0 }], compile: ({ vars: [e = 0], ...t }) => a[t.lang].defUgen(t, e) }), be2 = o("sine", { tags: ["regular", "waveform", "source"], ugen: "SineOsc", description: "Sine wave oscillator", examples: ["sine(220).out()"], ins: [{ name: "freq", default: 0 }, { name: "sync", default: 0, description: "sync input" }, { name: "phase", default: 0, description: "phase offset" }], compile: ({ vars: [e = 0, t = 0, i = 0], ...n }) => a[n.lang].defUgen(n, e, t, i) }), Re = o("tri", { ugen: "TriOsc", tags: ["regular", "waveform", "source"], description: "Triangle wave oscillator", examples: ["tri(220).out()"], ins: [{ name: "freq", default: 0 }], compile: ({ vars: [e = 0], ...t }) => a[t.lang].defUgen(t, e) }), Me2 = o("pulse", { ugen: "PulseOsc", tags: ["regular", "waveform", "source"], description: "Pulse wave oscillator", examples: ["pulse(220, sine(.1).range(.1,.5)).mul(.5).out()"], ins: [{ name: "freq", default: 0 }, { name: "pw", default: 0.5, description: "pulse width 0 - 1" }], compile: ({ vars: [e = 0, t = 0.5], ...i }) => a[i.lang].defUgen(i, e, t) }), Le = o("slide", { ugen: "Slide", tags: ["fx"], internal: true, description: "Slide/portamento node", examples: [`impulse(2).seq(55,110,220,330)
.slide(4).sine().out()`], ins: [{ name: "in", default: 0 }, { name: "rate", default: 1 }], compile: ({ vars: [e = 0, t = 1], ...i }) => a[i.lang].defUgen(i, e, t) }), xe2 = o("lag", { ugen: "Lag", tags: ["fx"], description: "Smoothes a signal. Good for slide / portamento effects.", examples: [`impulse(2).seq(220,330,440,550)
.lag(.4).sine().out()`], ins: [{ name: "in", default: 0 }, { name: "rate", default: 1, description: "60 dB lag time in seconds" }], compile: ({ vars: [e = 0, t = 1], ...i }) => a[i.lang].defUgen(i, e, t) }), ze2 = o("slew", { ugen: "Slew", tags: ["fx"], description: "Limits the slope of an input signal. The slope is expressed in units per second.", examples: ["pulse(800).slew(4000, 4000).out()"], ins: [{ name: "in", default: 0 }, { name: "up", default: 1, description: "Maximum upward slope in units per second" }, { name: "dn", default: 1, description: "Maximum downward slope in units per second" }], compile: ({ vars: [e = 0, t = 1, i = 1], ...n }) => a[n.lang].defUgen(n, e, t, i) }), j2 = o("filter", { ugen: "Filter", tags: ["fx", "filter"], internal: true, description: "Two-pole low-pass filter", examples: ["saw(55).lpf( sine(1).range(.4,.8) ).out()"], ins: [{ name: "in", default: 0 }, { name: "cutoff", default: 1 }, { name: "reso", default: 0 }], compile: ({ vars: [e = 0, t = 1, i = 0], ...n }) => a[n.lang].defUgen(n, e, t, i) }), Ve = o("fold", { ugen: "Fold", tags: ["fx", "distortion", "limiter"], description: 'Distort incoming audio signal by "folding"', examples: [`sine(55)
.fold( sine(.5).range(0.2,4) )
.out()`], ins: [{ name: "in", default: 0 }, { name: "rate", default: 0 }], compile: ({ vars: [e = 0, t = 0], ...i }) => a[i.lang].defUgen(i, e, t) }), We = o("seq", { ugen: "Sequence", tags: ["sequencer"], description: "Trigger controlled sequencer", examples: [`impulse(2).seq(220,330,440,550)
.sine().out()`], ins: [{ name: "trig", default: 0 }, { name: "step", default: 0, dynamic: true, description: "step inputs" }], compile: ({ vars: e, ...t }) => a[t.lang].defUgen(t, ...e) }), Ye2 = o("delay", { ugen: "Delay", tags: ["fx"], description: "Delay line node", examples: [`impulse(1).ad(.01,.2).mul(sine(220))
.add(x=>x.delay(.1).mul(.8)).out()`], ins: [{ name: "in", default: 0 }, { name: "time", default: 0 }], compile: ({ vars: [e = 0, t = 0], ...i }) => a[i.lang].defUgen(i, e, t) }), Ne = o("hold", { ugen: "Hold", tags: ["fx"], description: "Sample and hold", examples: [`noise().hold(impulse(2))
.range(220,880).sine().out()`], ins: [{ name: "in", default: 0 }, { name: "trig", default: 0 }], compile: ({ vars: [e = 0, t = 0], ...i }) => a[i.lang].defUgen(i, e, t) }), He = o("midifreq", { ugen: "MidiFreq", tags: ["external", "midi"], description: "Outputs frequency of midi note in. Multiple instances will do voice allocation", examples: ["midifreq().sine().out()"], ins: [{ name: "channel", default: -1, description: "Channel filter. Defaults to all channels" }], compile: ({ vars: [e = -1], ...t }) => a[t.lang].defUgen(t, e) }), Se2 = o("midigate", { ugen: "MidiGate", tags: ["external", "midi"], description: "outputs gate of midi note in. Multiple instances will do voice allocation", examples: ["midigate().lag(1).mul(sine(220)).out()"], ins: [{ name: "channel", default: -1 }], compile: ({ vars: [e = -1], ...t }) => a[t.lang].defUgen(t, e) }), we2 = o("midivel", { ugen: "MidiVel", tags: ["external", "midi"], description: "outputs velocity of midi note in. Multiple instances will do voice allocation", examples: ["midigate().ar(0.01,0.2).mul(saw(midifreq())).mul(midivel()).mul(.8).out()"], ins: [{ name: "channel", default: -1 }], compile: ({ vars: [e = -1], ...t }) => a[t.lang].defUgen(t, e) }), Te2 = o("midicc", { ugen: "MidiCC", tags: ["external", "midi"], description: "Outputs bipolar value of given midi cc number. initValue can be set to be the output before getting first cc message.", examples: ["midicc(74).range(100,200).sine().out()"], ins: [{ name: "ccnumber", default: -1 }, { name: "channel", default: -1 }, { name: "initValue", default: -1 }], compile: ({ vars: [e = -1, t = -1], ...i }) => a[i.lang].defUgen(i, e, t) }), N2 = o("cc", { ugen: "CC", tags: ["external"], description: "CC control", ins: [{ name: "id", default: 0 }, { name: "value", default: 0 }], compile: ({ vars: [e], ...t }) => a[t.lang].defUgen(t, e) }), Ke2 = o("audioin", { ugen: "AudioIn", tags: ["source", "external"], description: "External Audio Input, depends on your system input", examples: ["audioin().add(x=>x.delay(.1).mul(.8)).out()"], ins: [], compile: (e) => a[e.lang].defUgen(e, "input") }), H = o("log", { tags: ["math"], description: "calculates the logarithm (base 10) of the input signal", ins: [{ name: "in" }], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, a[i].log(e)) }), Q2 = o("exp", { tags: ["math"], description: "raises e to the power of the input signal", ins: [{ name: "in" }], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, a[i].exp(e)) }), Ce2 = o("pow", { tags: ["math"], description: "raises the input to the given power", ins: [{ name: "in" }, { name: "power" }], compile: ({ vars: [e = 0, t = 1], name: i, lang: n }) => a[n].def(i, a[n].pow(e, t)) }), B2 = o("sin", { tags: ["math"], description: "calculates the sine of the input signal", ins: [{ name: "in" }], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, a[i].defSin(e)) }), E2 = o("cos", { tags: ["math"], description: "calculates the cosine of the input signal", ins: [{ name: "in" }], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, a[i].defCos(e)) }), ve2 = o("tan", { tags: ["math"], description: "calculates the tan of the input signal", ins: [{ name: "in" }], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, a[i].defTan(e)) }), Ie = o("acos", { tags: ["math"], description: "calculates the acos of the input signal", ins: [{ name: "in" }], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, a[i].defAcos(e)) }), Ue2 = o("asin", { tags: ["math"], description: "calculates the asin of the input signal", ins: [{ name: "in" }], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, a[i].defAsin(e)) }), ke2 = o("atan", { tags: ["math"], description: "calculates the atan of the input signal", ins: [{ name: "in" }], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, a[i].defAtan(e)) }), Pe2 = o("mul", { tags: ["math"], description: "Multiplies the given signals.", examples: ["sine(220).mul( sine(4).range(.25,1) ).out()"], ins: [{ name: "in", dynamic: true }], compile: ({ vars: e, name: t, lang: i }) => a[i].def(t, e.join(" * ") || 0) }), S2 = o("add", { tags: ["math"], description: "sums the given signals", examples: ["n([0,3,7,10]).add(60).midinote().sine().mix(2).out()"], ins: [{ name: "in", dynamic: true }], compile: ({ vars: e, name: t, lang: i }) => a[i].def(t, e.join(" + ") || 0) }), Fe = o("div", { tags: ["math"], description: "adds the given signals", ins: [{ name: "in", dynamic: true }], compile: ({ vars: e, name: t, lang: i }) => a[i].def(t, e.join(" / ") || 0) }), Je = o("sub", { tags: ["math"], description: "subtracts the given signals", ins: [{ name: "in", dynamic: true }], compile: ({ vars: e, name: t, lang: i }) => a[i].def(t, e.join(" - ") || 0) }), je2 = o("mod", { tags: ["math"], description: "calculates the modulo", examples: ["add(x=>x.add(.003).mod(1)).out()"], ins: [{ name: "in" }, { name: "modulo" }], compile: ({ vars: e, name: t, lang: i }) => a[i].def(t, a[i].mod(...e) || 0) }), Qe2 = o("abs", { tags: ["math"], description: "returns the absolute value of the signal", ins: [{ name: "in" }], examples: ["sine(440).abs().out()"], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, a[i].abs(e)) }), Be2 = o("round", { tags: ["math"], description: "Rounds the signal to the nearest integer", ins: [{ name: "in" }], examples: ["sine(440.5).round().out()"], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, a[i].round(e)) }), Ee2 = o("clamp", { tags: ["math"], description: "Clamps the signal to stay within the given range", ins: [{ name: "in" }, { name: "min" }, { name: "max" }], examples: ["sine(440.5).clamp(-.6,.6).out()"], compile: ({ vars: [e = 0, t = -1, i = 1], name: n, lang: s }) => {
        const d2 = a[s].min(t, i), c2 = a[s].max(t, i), f2 = a[s].min(a[s].max(e, d2), c2);
        return a[s].def(n, f2);
      } }), Oe2 = o("floor", { tags: ["math"], description: "Rounds the signal down", ins: [{ name: "in" }], examples: ["sine(440.5).floor().out()"], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, a[i].floor(e)) }), $e = o("ceil", { tags: ["math"], description: "Rounds the signal up", ins: [{ name: "in" }], examples: ["sine(440.5).ceil().out()"], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, a[i].ceil(e)) }), Ae2 = o("sign", { tags: ["math"], description: "Returns 1 if positive and -1 if negative. uses Math.sign", ins: [{ name: "in" }], examples: ["sine(440.5).ceil().out()"], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, a[i].sign(e)) }), De = o("min", { tags: ["math"], description: "returns the minimum of the given signals", examples: ["impulse(4).apply(x => min(x.seq(0,3,2), x.seq(0,7,0,5,0)).add(48).midinote().sine()).out()"], ins: [{ name: "in", dynamic: true }], compile: ({ vars: e, name: t, lang: i }) => a[i].def(t, e.reduce(a[i].min) || 0) }), qe2 = o("max", { tags: ["math"], description: "returns the maximum of the given signals", examples: ["impulse(4).apply(x => max(x.seq(0,3,2), x.seq(0,7,0,5,0)).add(48).midinote().sine()).out()"], ins: [{ name: "in", dynamic: true }], compile: ({ vars: e, name: t, lang: i }) => a[i].def(t, e.reduce(a[i].max) || 0) }), _e2 = o("argmin", { tags: ["math"], description: "returns the index of the minimum of the given signals", examples: ["argmin(saw(1), saw(3), saw(5)).mul(12).add(48).midinote().sine().out()"], ins: [{ name: "in", dynamic: true }], compile: ({ vars: e, name: t, lang: i }) => a[i].def(t, a[i].pair_b(e.map(a[i].pair_make).reduce(a[i].pair_a_min)) || 0) }), et2 = o("argmax", { tags: ["math"], description: "returns the index of the maximum of the given signals", examples: ["argmax(saw(1), saw(3), saw(5)).mul(12).add(48).midinote().sine().out()"], ins: [{ name: "in", dynamic: true }], compile: ({ vars: e, name: t, lang: i }) => a[i].def(t, a[i].pair_b(e.map(a[i].pair_make).reduce(a[i].pair_a_max)) || 0) }), O = o("greater", { tags: ["logic"], description: "returns 1 if input is greater then threshold", ins: [{ name: "in" }, { name: "threshold" }], examples: [`greater(sine(1),0)
.bipolar().range(100,200)
.sine().out()`], compile: ({ vars: [e = 0, t = 0], name: i, lang: n }) => a[n].def(i, `${e} > ${t}`) }), $2 = o("lower", { tags: ["logic"], description: "returns 1 if input is lower then threshold", ins: [{ name: "in" }, { name: "threshold" }], examples: [`lower(sine(1),0)
.bipolar().range(100,200)
.sine().out()`], compile: ({ vars: [e = 0, t = 0], name: i, lang: n }) => a[n].def(i, `${e} < ${t}`) }), tt = O, it2 = $2, nt = o("xor", { tags: ["logic"], description: "returns 1 if exactly one of the inputs is 1", ins: [{ name: "a" }, { name: "b" }], compile: ({ vars: [e = 0, t = 0], name: i, lang: n }) => a[n].def(i, `${e} != ${t} ? 1 : 0`) }), lt2 = o("and", { tags: ["logic"], description: "returns 1 if both inputs are 1", ins: [{ name: "a" }, { name: "b" }], compile: ({ vars: [e = 0, t = 0], name: i, lang: n }) => a[n].def(i, `${e} && ${t} ? 1 : 0`) }), at2 = o("or", { tags: ["logic"], description: "returns 1 if one or both inputs are 1", ins: [{ name: "a" }, { name: "b" }], compile: ({ vars: [e = 0, t = 0], name: i, lang: n }) => a[n].def(i, `${e} || ${t} ? 1 : 0`) }), st = o("not", { tags: ["logic"], description: "returns 1 if input is 0, otherwise 0", ins: [{ name: "in" }], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, `(${e} === 0 ? 1 : 0)`) }), ot2 = o("bool", { tags: ["logic"], description: "returns 1 signal is non zero. inspired by genish", ins: [{ name: "a" }], compile: ({ vars: [e = 0], name: t, lang: i }) => a[i].def(t, `(${e} === 0 ? 0 : 1)`) }), dt2 = o("ifelse", { tags: ["logic"], description: "if control is 1, a is returned, otherwise b", ins: [{ name: "control" }, { name: "a" }, { name: "b" }], compile: ({ vars: [e = 0, t = 0, i = 0], name: n, lang: s }) => a[s].def(n, `(${e} === 1 ? ${t} : ${i})`), examples: ["ifelse(pulse(1), sine(220), sine(330)).out()"] }), ct2 = o("range", { tags: ["math"], description: "Scales the incoming bipolar value to the given range.", examples: ["sine(.5).range(.25,1).mul(sine(440)).out()"], ins: [{ name: "in" }, { name: "min" }, { name: "max" }], compile: ({ vars: e, name: t, lang: i }) => {
        const [n, s, d2, c2 = 1] = e, f2 = `((${n} + 1) * 0.5)`, p = c2 === 1 ? f2 : a[i].pow(f2, c2);
        return a[i].def(t, `${p} * (${d2} - ${s}) + ${s}`);
      } }), ut2 = o("remap", { ugen: "Remap", tags: ["math"], description: "Remaps input from one value range to another", ins: [{ name: "in" }, { name: "inmin" }, { name: "inmax" }, { name: "outmin" }, { name: "outmax" }], compile: ({ vars: [e = 0, t = -1, i = 1, n = -1, s = 1], ...d2 }) => a[d2.lang].defUgen(d2, e, t, i, n, s) }), pt2 = o("thru", { compile: ({ name: e, vars: t, lang: i }) => a[i].def(e, t[0], "thru") }), mt2 = g("rangex", (e, t, i) => {
        let n = H(t), s = H(i).sub(n), c2 = e.unipolar().mul(s).add(n);
        return Q2(c2);
      }, { tags: ["math"], description: "exponential range", ins: [{ name: "in" }, { name: "min" }, { name: "max" }], examples: ["sine([1,3]).rangex(100, 2e3).sine().out()"] }), rt2 = o("midinote", { compile: ({ vars: [e], name: t, lang: i }) => a[i].def(t, a[i].midinote(e)), tags: ["math"], description: "convert midi number to frequency", ins: [{ name: "midi" }], examples: [`impulse(4).seq(0,3,7,12).add(60)
.midinote().sine().out()`] }), ht = o("src", { internal: true, compile: ({ vars: [e = 0], name: t, lang: i, ...n }) => a[i].def(t, n.getSource(e), `read source ${e}`) }), Gt = o("output", { internal: true, ugen: "Output", compile: ({ vars: [e, t = 0], name: i, lang: n, ...s }) => {
        const d2 = s.getOutput(t), c2 = s.getSource(t);
        return [a[n].def(d2, [d2, e].join(" + "), `+ output ${t}`), a[n].def(c2, d2, `write source ${t}`)].join(`
`);
      } }), A = o("poly"), D = X(Math.PI), yt2 = m2("fork", (e, t = 1) => A(...Array.from({ length: t }, () => e.clone())), { ins: [{ name: "in" }, { name: "times" }], tags: ["multi-channel"], description: "split the signal into n channels", examples: ["dust(4).fork(2).adsr(.1).mul(sine(220)).out()"] }), ft = g("perc", (e, t) => e.adsr(0, 0, 1, t), { tags: ["envelope"], description: "percussive envelope. usable with triggers or gates", ins: [{ name: "gate" }, { name: "release" }], examples: ["impulse(4).perc(.1).mul( pink() ).out()"] }), gt2 = g("hpf", (e, t, i = 0) => e.sub(e.lpf(t, i)), { ins: [{ name: "in" }, { name: "cutoff" }, { name: "reso" }], description: "high pass filter", tags: ["fx", "filter"], examples: ["tri([220,331,442]).mix().hpf(sine(.5).range(0,.9)).out()"] }), Xt2 = g("lpf", j2, { ins: [{ name: "in" }, { name: "cutoff" }, { name: "reso" }], description: "low pass filter", tags: ["fx", "filter"], examples: ["saw(55).lpf( sine(1).range(.4,.8) ).out()"] }), Zt2 = o("bpf", { ugen: "BPF", ins: [{ name: "in" }, { name: "cutoff" }, { name: "reso" }], description: "high pass filter", tags: ["fx", "filter"], compile: ({ vars: [e = 0, t = 1, i = 0], ...n }) => a[n.lang].defUgen(n, e, t, i) }), bt2 = g("lfnoise", (e) => F2().hold(J2(e)), { ins: [{ name: "freq" }], description: "low frequency stepped noise.", tags: ["regular", "noise"], examples: ["lfnoise(4).range(200,800).sine().out()"] }), Rt2 = g("bipolar", (e) => X(e).mul(2).sub(1), { ins: [{ name: "in" }], description: "convert unipolar [0,1] signal to bipolar [-1,1]", tags: ["math"] }), Mt2 = g("unipolar", (e) => X(e).add(1).div(2), { ins: [{ name: "in" }], description: "convert bipolar [-1,1] signal to unipolar [0,1]", tags: ["math"] }), Lt2 = g("pan", (e, t) => (t = X(t).add(1).mul(D, 0.25), e.mul([E2(t), B2(t)])), { ins: [{ name: "in" }, { name: "pos", description: "bipolar position: -1 = left, 0 = center, 1 = right" }], description: "pans signal to stereo position. splits signal path in 2", tags: ["multi-channel"], examples: ["sine(220).pan(sine(.25)).out()"] }), xt2 = o("pick", { tags: ["multi-channel"], ugen: "Pick", description: "Pick", ins: [{ name: "index" }, { name: "inputs", dynamic: true }], description: "picks input of given index", examples: [`sine(.25).range(0,2).round()
.pick(...sine([220,330,440]).ins)
.out()`], compile: ({ vars: e, ...t }) => a[t.lang].defUgen(t, ...e) }), zt2 = o("clip", { tags: ["fx"], ugen: "Clip", description: "Hard limits the signal between lo and hi.", ins: [{ name: "input" }, { name: "lo" }, { name: "hi" }], compile: ({ vars: [e = 0, t = -1, i = 1], ...n }) => a[n.lang].defUgen(n, e, t, i) }), Vt = o("trig", { tags: ["trigger"], ugen: "Trig", description: "Emits a trigger impulse whenever the signal becomes positive. Useful to turn gates into triggers.", ins: [{ name: "input", default: 0 }, { name: "lo", default: -1 }, { name: "hi", default: 1 }], compile: ({ vars: [e = 0, t = -1, i = 1], ...n }) => a[n.lang].defUgen(n, e, t, i), examples: [`pulse(2)
.trig() // comment out to hear difference
.ar(.01,.2)
.mul(sine(200)).out()`] }), Wt2 = o("qf", { tags: ["fx", "filter"], ugen: "BiquadFilter", description: "biQuad Filter.", ins: [{ name: "input", default: 0 }, { name: "type", default: 0, description: "filter type: 0 = lowpass, 1 = highpass, 2 = band pass, 3 = notch, 4 = allpass, 5 = peaking, 6 = lowshelf, 7 = highshelf" }, { name: "freq", default: 500, description: "filter cutoff in Hz" }, { name: "q", default: 1, description: "q factor" }, { name: "gain", default: 1 }], compile: ({ vars: e, ...t }) => a[t.lang].defUgen(t, ...e), examples: [`pink()
.qf(
 impulse(.5).seq(0,1,2,3,4,5,6,7), // type
  tri(0.5).rangex(100, 8000),  // freq
 10, // Q
 1, // gain (only relevant for types 5-7)
).div(4).out();`] }), Yt2 = m2("qlpf", (e, t, i = 10) => e.qf(0, t, i), { description: "biQuad Low Pass Filter", ins: [{ name: "input" }, { name: "freq" }, { name: "q", description: "resonance" }], tags: ["fx", "filter"], examples: [`pink().qlpf(
  tri(0.5).rangex(100, 8000), // cutoff freq
  10 // Q
).out()`] }), Nt2 = m2("qhpf", (e, t, i = 10) => e.qf(1, t, i), { description: "biQuad High pass filter", ins: [{ name: "input" }, { name: "freq" }, { name: "q", description: "resonance" }], tags: ["fx", "filter"], examples: [`pink().qhpf(
  tri(0.5).rangex(100, 8000), // cutoff freq
  10 // Q
).out()`] }), Ht = m2("qbpf", (e, t, i = 10) => e.qf(2, t, i), { description: "biQuad Band Pass Filter", ins: [{ name: "input" }, { name: "freq" }, { name: "q", description: "resonance" }], tags: ["fx", "filter"], examples: [`pink().qbpf(
  tri(0.5).rangex(100, 8000), // cutoff freq
  10 // Q
).out()`] }), St = m2("qnf", (e, t, i = 10) => e.qf(3, t, i), { description: "biQuad Notch Filter", ins: [{ name: "input" }, { name: "freq" }, { name: "q", description: "resonance" }], tags: ["fx", "filter"], examples: [`pink().qnf(
  tri(0.5).rangex(100, 8000), // cutoff freq
  10 // Q
).out()`] }), wt2 = m2("qapf", (e, t, i = 10) => e.qf(3, t, i), { description: "biQuad All Pass Filter", ins: [{ name: "input" }, { name: "freq" }, { name: "q", description: "resonance" }], tags: ["fx", "filter"], examples: [`impulse(1).qapf(
  tri(0.5).rangex(100, 8000), // cutoff freq
  10 // Q
).out()`] }), Tt = m2("split", (e, t) => e.type !== "poly" ? t([e]) : t(e.ins), { ins: [{ name: "input" }, { name: "fn" }], tags: ["multi-channel"], description: "apply fn to an array of signals, one for each channel in input", examples: ["sine([220,330,550]).split(chs => add(...chs)).out()"] }), Kt2 = m2("mix", (e, t = 1) => {
        if ([1, 2].includes(t) || (t = 2, console.warn("mix only supports 1 or 2 channels atm.. falling back to 2")), e.type !== "poly") return e;
        if (t === 2) {
          const i = e.ins.map((n, s, d2) => {
            const f2 = (s / (d2.length - 1) * 2 - 1 + 1) * Math.PI / 4;
            return n.mul([Math.cos(f2), Math.sin(f2)]).inherit(e);
          });
          return S2(...i);
        }
        return e.ins = e.ins.map((i) => i.inherit(e)), R2("mix").withIns(...e.ins);
      }, { compile: ({ vars: e, name: t, lang: i }) => a[i].def(t, `(${e.join(" + ")})`), description: `mixes down multiple channels. Useful to make sure you get a mono or stereo signal out at the end. 
When mixing down to 2 channels, the input channels are equally distributed over the stereo image, e.g. 3 channels are panned [-1,0,1]`, ins: [{ name: "in" }, { name: "channels", default: 1, description: "how many channels to mix down to. Only supports 1 and 2" }], tags: ["multi-channel"], examples: ["sine([220,330,440]).mix(2).out()"] });
      u.prototype.feedback = function(e) {
        return this.add(e);
      };
      let Ct2 = (e) => S2(e), vt2 = X, It2 = X, Ut2 = g("mouseX", () => N2("mouseX"), { ins: [], description: "X position of mouse, bipolar range", tags: ["external"], examples: ["mouseX.range(100,800).sine().out()"] })(), kt2 = g("mouseY", () => N2("mouseY"), { ins: [], description: "Y position of mouse, bipolar range", tags: ["external"], examples: ["mouseY.range(800,100).sine().out()"] })(), Pt2 = m2("scope", (e, t) => {
        let i = 1;
        e.type === "poly" && (i = e.ins.length);
        const n = getNode("scope", e, t, i);
        return n.type !== "poly" ? (n.ins.push({ type: "n", value: 0, ins: [] }), n) : (n.ins.forEach((s, d2) => s.ins.push({ type: "n", value: d2, ins: [] })), n);
      }, { ugen: "Scope", description: "renders an an oscilloscope of the current point in the graph. expects values between -1 and 1. warning: this feature is still experimental! when using it, make sure to not switch tabs, as it might fry your browser.", compile: ({ vars: [e, t, i, n], ...s }) => U2(s, e, t, i, n) });
      const Ft2 = Object.freeze(Object.defineProperty({ __proto__: null, B: vt2, PI: D, _: It2, abs: Qe2, acos: Ie, ad: pe2, add: S2, adsr: ce2, and: lt2, ar: ue2, argmax: et2, argmin: _e2, asin: Ue2, atan: ke2, audioin: Ke2, bipolar: Rt2, bool: ot2, bpf: Zt2, brown: fe2, bytebeat: oe2, cc: N2, ceil: $e, clamp: Ee2, clip: zt2, clock: me2, clockdiv: re2, cos: E2, delay: Ye2, distort: he2, div: Fe, dust: ge2, exp: Q2, feedback: Ct2, filter: j2, floatbeat: de2, floor: Oe2, fold: Ve, fork: yt2, greater: O, gt: tt, hold: Ne, hpf: gt2, ifelse: dt2, impulse: J2, lag: xe2, lfnoise: bt2, log: H, lower: $2, lpf: Xt2, lt: it2, max: qe2, midicc: Te2, midifreq: He, midigate: Se2, midinote: rt2, midivel: we2, min: De, mix: Kt2, mod: je2, mouseX: Ut2, mouseY: kt2, mul: Pe2, noise: F2, not: st, or: at2, output: Gt, pan: Lt2, perc: ft, pick: xt2, pink: ye2, poly: A, pow: Ce2, pulse: Me2, qapf: wt2, qbpf: Ht, qf: Wt2, qhpf: Nt2, qlpf: Yt2, qnf: St, range: ct2, rangex: mt2, raw: se2, registerUgen: P2, remap: ut2, rng: Ge2, round: Be2, saw: Xe2, scope: Pt2, seq: We, sign: Ae2, sin: B2, sine: be2, slew: ze2, slide: Le, split: Tt, src: ht, sub: Je, tan: ve2, thru: pt2, time: ae2, tri: Re, trig: Vt, unipolar: Mt2, xor: nt, zaw: Ze2 }, Symbol.toStringTag, { value: "Module" }));
      class Ji2 {
        constructor({ onToggle: t, onToggleRecording: i, beforeEval: n, transpiler: s, localScope: d2 = false, outputNode: c2 = null } = {}) {
          this.outputNode = c2, this.audio = new le2(this.outputNode), this.onToggle = t, this.transpiler = s, this.onToggleRecording = i, this.beforeEval = n, this.localScope = d2, typeof window < "u" && (d2 || (Object.assign(globalThis, ie2), Object.assign(globalThis, Ft2), Object.assign(globalThis, ee2), Object.assign(globalThis, { repl: this })), window.addEventListener("message", (p) => {
            p.data.type === "KABELSALAT_SET_CONTROL" && this.audio.setControl(p.data.id, p.data.value);
          }));
          const f2 = this;
          u.prototype.spawn = function(p = [0, 1], h) {
            f2.audio.spawn(this.output(p).exit(), h);
          };
        }
        registerUgen(t, i) {
          return this.audio.registerUgen(i), P2(t, i.name);
        }
        evaluate(t) {
          this.localScope || (Object.assign(globalThis, { audio: this.audio }), Object.assign(globalThis, { addUgen: this.registerUgen.bind(this) }));
          let i;
          this.transpiler ? i = this.transpiler(t) : i = { output: t }, this.beforeEval?.(i);
          let n;
          return this.localScope && (n = { ...ie2, ...Ft2, ...ee2, audio: this.audio, addUgen: this.registerUgen.bind(this), repl: this }), v(i.output, n);
        }
        async play(t) {
          await this.audio.init(), t.ins.length && this.audio.spawn(t), this.onToggle?.(true);
        }
        run(t) {
          const i = this.evaluate(t);
          this.play(i);
        }
        stop() {
          this.stopRecording(), this.audio.stop(), this.onToggle?.(false);
        }
        record() {
          this.audio.record(), this.onToggleRecording?.(true);
        }
        stopRecording() {
          this.audio.stopRecording(), this.onToggleRecording?.(false);
        }
      }
      return l2.AudioView = le2, l2.B = vt2, l2.Node = u, l2.PI = D, l2.SalatRepl = Ji2, l2._ = It2, l2.abs = Qe2, l2.acos = Ie, l2.ad = pe2, l2.add = S2, l2.adsr = ce2, l2.and = lt2, l2.ar = ue2, l2.argmax = et2, l2.argmin = _e2, l2.asin = Ue2, l2.atan = ke2, l2.audioin = Ke2, l2.bipolar = Rt2, l2.bool = ot2, l2.bpf = Zt2, l2.brown = fe2, l2.bytebeat = oe2, l2.cc = N2, l2.ceil = $e, l2.clamp = Ee2, l2.clip = zt2, l2.clock = me2, l2.clockdiv = re2, l2.compile = W2, l2.cos = E2, l2.delay = Ye2, l2.distort = he2, l2.div = Fe, l2.dust = ge2, l2.evaluate = v, l2.exit = C2, l2.exp = Q2, l2.exportModule = _, l2.feedback = Ct2, l2.filter = j2, l2.floatbeat = de2, l2.floor = Oe2, l2.fold = Ve, l2.fork = yt2, l2.getInletName = q2, l2.getNode = K2, l2.greater = O, l2.gt = tt, l2.hold = Ne, l2.hpf = gt2, l2.ifelse = dt2, l2.impulse = J2, l2.lag = xe2, l2.lfnoise = bt2, l2.log = H, l2.lower = $2, l2.lpf = Xt2, l2.lt = it2, l2.max = qe2, l2.midicc = Te2, l2.midifreq = He, l2.midigate = Se2, l2.midinote = rt2, l2.midivel = we2, l2.min = De, l2.mix = Kt2, l2.mod = je2, l2.module = g, l2.mouseX = Ut2, l2.mouseY = kt2, l2.mul = Pe2, l2.n = X, l2.node = R2, l2.nodeRegistry = r, l2.noise = F2, l2.not = st, l2.or = at2, l2.output = Gt, l2.outputType = V2, l2.pan = Lt2, l2.perc = ft, l2.pick = xt2, l2.pink = ye2, l2.poly = A, l2.polyType = b, l2.pow = Ce2, l2.pulse = Me2, l2.qapf = wt2, l2.qbpf = Ht, l2.qf = Wt2, l2.qhpf = Nt2, l2.qlpf = Yt2, l2.qnf = St, l2.range = ct2, l2.rangex = mt2, l2.raw = se2, l2.register = m2, l2.registerNode = o, l2.registerUgen = P2, l2.remap = ut2, l2.rng = Ge2, l2.round = Be2, l2.saw = Xe2, l2.scope = Pt2, l2.seq = We, l2.sign = Ae2, l2.signal = Mi2, l2.sin = B2, l2.sine = be2, l2.slew = ze2, l2.slide = Le, l2.split = Tt, l2.src = ht, l2.sub = Je, l2.tan = ve2, l2.thru = pt2, l2.time = ae2, l2.tri = Re, l2.trig = Vt, l2.unipolar = Mt2, l2.xor = nt, l2.zaw = Ze2, Object.defineProperty(l2, Symbol.toStringTag, { value: "Module" }), l2;
    })({});
  }
});

// outputs/skycam/labs/strudel/node_modules/@strudel/core/dist/index.mjs
var dist_exports = {};
__export(dist_exports, {
  ClockCollator: () => _n,
  Cyclist: () => hf,
  FXr: () => uf,
  FXrel: () => cf,
  FXrelease: () => of,
  Fraction: () => m,
  Hap: () => S,
  Pattern: () => f,
  State: () => ut,
  TimeSpan: () => B,
  __chooseWith: () => Me,
  _brandBy: () => Oe,
  _fitslice: () => Fn,
  _irand: () => ze,
  _keyDown: () => je,
  _match: () => In,
  _mod: () => bt,
  _morph: () => de,
  _polymeterListSteps: () => Hn,
  _retime: () => Yt,
  _slices: () => Zt,
  accelerate: () => Ys,
  activeLabel: () => va,
  ad: () => Bp,
  add: () => $h,
  adsr: () => xp,
  almostAlways: () => Jw,
  almostNever: () => jw,
  always: () => Nw,
  amp: () => sr,
  analyze: () => gc,
  anchor: () => Ua,
  and: () => nd,
  apply: () => Pd,
  applyN: () => Wn,
  ar: () => zp,
  arp: () => wh,
  arpWith: () => yh,
  arrange: () => kh,
  as: () => Kp,
  asym: () => py,
  att: () => or,
  attack: () => rr,
  averageArray: () => nn,
  backgroundImage: () => Hw,
  band: () => Ih,
  bandf: () => Cc,
  bandq: () => Oc,
  bank: () => yc,
  base64ToUnicode: () => gn,
  bbexpr: () => ti,
  bbst: () => ni,
  beat: () => oy,
  begin: () => Mc,
  berlin: () => qw,
  bgain: () => ja,
  binary: () => iw,
  binaryL: () => uw,
  binaryN: () => Jf,
  binaryNL: () => $f,
  bind: () => xh,
  binshift: () => Zl,
  bite: () => Ld,
  bjork: () => _y,
  bjorklund: () => ge,
  blshift: () => Dh,
  bmod: () => sf,
  bor: () => Vh,
  bp: () => Bc,
  bpa: () => ji,
  bpattack: () => Ei,
  bpd: () => Wi,
  bpdc: () => yu,
  bpdecay: () => Ri,
  bpdepth: () => fu,
  bpdepthfreq: () => du,
  bpdepthfrequency: () => hu,
  bpe: () => Bi,
  bpenv: () => xi,
  bpf: () => xc,
  bpq: () => zc,
  bpr: () => Zi,
  bprate: () => lu,
  bprelease: () => Yi,
  bps: () => Gi,
  bpshape: () => mu,
  bpskew: () => wu,
  bpsustain: () => Di,
  bpsync: () => pu,
  brak: () => Ud,
  brand: () => mw,
  brandBy: () => dw,
  brshift: () => Gh,
  bus: () => Pa,
  busgain: () => Ea,
  bxor: () => Hh,
  bypass: () => Tm,
  byteBeatExpression: () => Zc,
  byteBeatStartTime: () => ei,
  calculateSteps: () => dh,
  cat: () => mt,
  ccn: () => $p,
  ccv: () => Np,
  ceil: () => id,
  ch: () => ri,
  channel: () => gi,
  channels: () => si,
  chebyshev: () => dy,
  choose: () => Rf,
  chooseCycles: () => Wf,
  chooseIn: () => ww,
  chooseInWith: () => Pe,
  chooseOut: () => gw,
  chooseWith: () => It,
  chop: () => Xm,
  chord: () => Da,
  chorus: () => wc,
  chunk: () => mm,
  chunkBack: () => gm,
  chunkBackInto: () => Am,
  chunkInto: () => qm,
  chunkback: () => bm,
  chunkbackinto: () => Sm,
  chunkinto: () => km,
  clamp: () => an,
  cleanupUi: () => Dw,
  clip: () => pp,
  coarse: () => Rc,
  code2hash: () => ph,
  color: () => Ap,
  colour: () => Tp,
  comb: () => Xl,
  compose: () => oh,
  compress: () => dd,
  compressSpan: () => md,
  compressor: () => bl,
  compressorAttack: () => kl,
  compressorKnee: () => _l,
  compressorRatio: () => vl,
  compressorRelease: () => ql,
  compressspan: () => yd,
  constant: () => ch,
  contract: () => Kn,
  control: () => Jp,
  controls: () => gy,
  cosine: () => Qy,
  cosine2: () => Uy,
  cpm: () => Ed,
  cps: () => lp,
  createClock: () => ff,
  createParam: () => Nt,
  createParams: () => Cp,
  crush: () => Lc,
  ctf: () => vi,
  ctlNum: () => Lp,
  ctranspose: () => Aa,
  cubic: () => ay,
  curry: () => w,
  curve: () => yp,
  cut: () => bi,
  cutoff: () => _i,
  cycleToSeconds: () => Kt,
  cyclesPer: () => Ww,
  dec: () => vc,
  decay: () => _c,
  degrade: () => Tw,
  degradeBy: () => Aw,
  degradeByWith: () => Sw,
  degree: () => qa,
  delay: () => Ru,
  delayfb: () => Fu,
  delayfeedback: () => Wu,
  delayspeed: () => Vu,
  delaysync: () => Qu,
  delayt: () => Du,
  delaytime: () => Hu,
  deltaSlide: () => wp,
  det: () => Ku,
  detune: () => Xu,
  dfb: () => Iu,
  dict: () => Qa,
  dictionary: () => Ga,
  diode: () => ly,
  dist: () => yl,
  distort: () => ml,
  distorttype: () => gl,
  distortvol: () => wl,
  div: () => Rh,
  djf: () => Lu,
  drawLine: () => Cn,
  drive: () => Qc,
  drop: () => Qn,
  dry: () => ta,
  ds: () => Op,
  dt: () => Gu,
  duck: () => Uc,
  duckattack: () => Yc,
  duckdepth: () => Xc,
  duckonset: () => Kc,
  dur: () => dp,
  duration: () => hp,
  early: () => jd,
  echo: () => im,
  echoWith: () => sm,
  echowith: () => rm,
  eish: () => Ty,
  end: () => Pc,
  enhance: () => Ul,
  env: () => nf,
  eq: () => Yh,
  eqt: () => Zh,
  errorLogger: () => zt,
  euclid: () => by,
  euclidLegato: () => qy,
  euclidLegatoRot: () => Sy,
  euclidRot: () => ky,
  euclidish: () => Ay,
  euclidrot: () => vy,
  evalScope: () => xn,
  evaluate: () => On,
  every: () => Md,
  expand: () => Xn,
  expression: () => Ol,
  extend: () => Un,
  fadeInTime: () => sa,
  fadeOutTime: () => na,
  fadeTime: () => ea,
  fanchor: () => eu,
  fast: () => qd,
  fastChunk: () => vm,
  fastGap: () => wd,
  fastcat: () => N,
  fastchunk: () => _m,
  fastgap: () => gd,
  fft: () => bc,
  filter: () => zm,
  filterWhen: () => Mm,
  firstOf: () => zd,
  fit: () => ey,
  flatten: () => G,
  floor: () => cd,
  fm: () => Sr,
  fm1: () => Ar,
  fm2: () => Tr,
  fm3: () => Cr,
  fm4: () => xr,
  fm5: () => Br,
  fm6: () => Or,
  fm7: () => zr,
  fm8: () => Mr,
  fmatt: () => Kr,
  fmatt1: () => Yr,
  fmatt2: () => Zr,
  fmatt3: () => to,
  fmatt4: () => eo,
  fmatt5: () => no,
  fmatt6: () => so,
  fmatt7: () => ro,
  fmatt8: () => oo,
  fmattack: () => Fr,
  fmattack1: () => Ir,
  fmattack2: () => Vr,
  fmattack3: () => Hr,
  fmattack4: () => Dr,
  fmattack5: () => Gr,
  fmattack6: () => Qr,
  fmattack7: () => Ur,
  fmattack8: () => Xr,
  fmdec: () => Ao,
  fmdec1: () => To,
  fmdec2: () => Co,
  fmdec3: () => xo,
  fmdec4: () => Bo,
  fmdec5: () => Oo,
  fmdec6: () => zo,
  fmdec7: () => Mo,
  fmdec8: () => Po,
  fmdecay: () => yo,
  fmdecay1: () => wo,
  fmdecay2: () => go,
  fmdecay3: () => bo,
  fmdecay4: () => _o,
  fmdecay5: () => vo,
  fmdecay6: () => ko,
  fmdecay7: () => qo,
  fmdecay8: () => So,
  fmenv: () => Pr,
  fmenv1: () => Er,
  fmenv2: () => jr,
  fmenv3: () => Jr,
  fmenv4: () => $r,
  fmenv5: () => Nr,
  fmenv6: () => Lr,
  fmenv7: () => Rr,
  fmenv8: () => Wr,
  fmh: () => cr,
  fmh1: () => ir,
  fmh2: () => ur,
  fmh3: () => ar,
  fmh4: () => lr,
  fmh5: () => pr,
  fmh6: () => fr,
  fmh7: () => hr,
  fmh8: () => dr,
  fmi: () => mr,
  fmi1: () => yr,
  fmi2: () => wr,
  fmi3: () => gr,
  fmi4: () => br,
  fmi5: () => _r,
  fmi6: () => vr,
  fmi7: () => kr,
  fmi8: () => qr,
  fmrel: () => ic,
  fmrel1: () => uc,
  fmrel2: () => ac,
  fmrel3: () => lc,
  fmrel4: () => pc,
  fmrel5: () => fc,
  fmrel6: () => hc,
  fmrel7: () => dc,
  fmrel8: () => mc,
  fmrelease: () => Yo,
  fmrelease1: () => Zo,
  fmrelease2: () => tc,
  fmrelease3: () => ec,
  fmrelease4: () => nc,
  fmrelease5: () => sc,
  fmrelease6: () => rc,
  fmrelease7: () => oc,
  fmrelease8: () => cc,
  fmsus: () => Io,
  fmsus1: () => Vo,
  fmsus2: () => Ho,
  fmsus3: () => Do,
  fmsus4: () => Go,
  fmsus5: () => Qo,
  fmsus6: () => Uo,
  fmsus7: () => Xo,
  fmsus8: () => Ko,
  fmsustain: () => Eo,
  fmsustain1: () => jo,
  fmsustain2: () => Jo,
  fmsustain3: () => $o,
  fmsustain4: () => No,
  fmsustain5: () => Lo,
  fmsustain6: () => Ro,
  fmsustain7: () => Wo,
  fmsustain8: () => Fo,
  fmwave: () => co,
  fmwave1: () => io,
  fmwave2: () => uo,
  fmwave3: () => ao,
  fmwave4: () => lo,
  fmwave5: () => po,
  fmwave6: () => fo,
  fmwave7: () => ho,
  fmwave8: () => mo,
  focus: () => bd,
  focusSpan: () => _d,
  focusspan: () => vd,
  fold: () => fy,
  fractionalArgs: () => ih,
  frameRate: () => np,
  frames: () => sp,
  freeze: () => Vl,
  freq: () => ra,
  freqToMidi: () => Ze,
  fromBipolar: () => ad,
  fshift: () => Ml,
  fshiftnote: () => Pl,
  fshiftphase: () => El,
  ftype: () => tu,
  func: () => rd,
  fxr: () => af,
  gain: () => er,
  gap: () => pt,
  gat: () => wa,
  gate: () => ya,
  getAccidentalsOffset: () => Ye,
  getControlName: () => yt,
  getCps: () => Fy,
  getCurrentKeyboardState: () => qn,
  getEventOffsetMs: () => th,
  getFreq: () => tn,
  getFrequency: () => rh,
  getIsStarted: () => Hy,
  getPattern: () => Iy,
  getPerformanceTimeSeconds: () => hh,
  getPlayableNoteValue: () => sh,
  getRandsAtTime: () => K,
  getSoundIndex: () => nh,
  getTime: () => Wy,
  getTrigger: () => Sf,
  getTriggerFunc: () => Vy,
  grow: () => jm,
  gt: () => Uh,
  gte: () => Kh,
  hard: () => uy,
  harmonic: () => Ta,
  hash2code: () => fh,
  hbrick: () => tp,
  hcutoff: () => Mu,
  hold: () => Tc,
  hours: () => rp,
  hp: () => Eu,
  hpa: () => Pi,
  hpattack: () => Mi,
  hpd: () => Li,
  hpdc: () => Su,
  hpdecay: () => Ni,
  hpdepth: () => _u,
  hpdepthfreq: () => ku,
  hpdepthfrequency: () => vu,
  hpe: () => Ci,
  hpenv: () => Ti,
  hpf: () => Pu,
  hpq: () => Ju,
  hpr: () => Ki,
  hprate: () => gu,
  hprelease: () => Xi,
  hps: () => Hi,
  hpshape: () => qu,
  hpskew: () => Au,
  hpsustain: () => Vi,
  hpsync: () => bu,
  hresonance: () => ju,
  hsl: () => Om,
  hsla: () => Bm,
  hurry: () => Ad,
  id: () => ot,
  imag: () => Ql,
  inhabit: () => Jy,
  inhabitmod: () => Ny,
  innerBind: () => Bh,
  inside: () => xd,
  inv: () => Dd,
  invert: () => Hd,
  ir: () => cl,
  irand: () => yw,
  irbegin: () => al,
  iresponse: () => il,
  irspeed: () => ul,
  isControlName: () => is,
  isNote: () => Mt,
  isNoteWithOctave: () => Yf,
  isPattern: () => pe,
  isaw: () => Rt,
  isaw2: () => Ae,
  iter: () => pm,
  iterBack: () => fm,
  iterback: () => hm,
  itri: () => Zy,
  itri2: () => tw,
  jux: () => nm,
  juxBy: () => tm,
  juxby: () => em,
  kcutoff: () => $l,
  keep: () => jh,
  keepif: () => Jh,
  keyAlias: () => kn,
  keyDown: () => Rw,
  krush: () => Jl,
  label: () => ka,
  lastOf: () => Od,
  late: () => Ln,
  lbrick: () => ep,
  legato: () => fp,
  leslie: () => ga,
  lfo: () => ef,
  linger: () => Rd,
  listRange: () => _t,
  lock: () => Uu,
  logKey: () => oe,
  logger: () => E,
  loop: () => Ec,
  loopAt: () => Zm,
  loopAtCps: () => ny,
  loopBegin: () => jc,
  loopEnd: () => $c,
  loopat: () => ty,
  loopatcps: () => sy,
  loopb: () => Jc,
  loope: () => Nc,
  lp: () => qi,
  lpa: () => zi,
  lpattack: () => Oi,
  lpd: () => $i,
  lpdc: () => uu,
  lpdecay: () => Ji,
  lpdepth: () => ru,
  lpdepthfreq: () => cu,
  lpdepthfrequency: () => ou,
  lpe: () => Ai,
  lpenv: () => Si,
  lpf: () => ki,
  lpq: () => Nu,
  lpr: () => Ui,
  lprate: () => nu,
  lprelease: () => Qi,
  lps: () => Ii,
  lpshape: () => iu,
  lpskew: () => au,
  lpsustain: () => Fi,
  lpsync: () => su,
  lrate: () => ba,
  lsize: () => _a,
  lt: () => Qh,
  lte: () => Xh,
  mapArgs: () => ie,
  mask: () => Sh,
  midi2note: () => eh,
  midiToFreq: () => it,
  midibend: () => Dp,
  midichan: () => Mp,
  midicmd: () => jp,
  midimap: () => Pp,
  midiport: () => Ep,
  miditouch: () => Gp,
  minutes: () => op,
  mod: () => Wh,
  mode: () => Ya,
  morph: () => cy,
  mouseX: () => ow,
  mouseY: () => sw,
  mousex: () => rw,
  mousey: () => nw,
  mtranspose: () => Sa,
  mul: () => Lh,
  n: () => Xs,
  nanFallback: () => sn,
  ne: () => td,
  net: () => ed,
  never: () => $w,
  noise: () => Bu,
  note: () => Ks,
  noteToMidi: () => gt,
  nothing: () => R,
  nrpnn: () => Rp,
  nrpv: () => Wp,
  nudge: () => Ba,
  numeralArgs: () => L,
  objectMap: () => bn,
  oct: () => za,
  octave: () => Oa,
  octaveR: () => xa,
  octaves: () => Ka,
  octer: () => Nl,
  octersub: () => Ll,
  octersubsub: () => Rl,
  off: () => Qd,
  offset: () => Xa,
  often: () => Pw,
  or: () => sd,
  orbit: () => Ma,
  oschost: () => Up,
  oscport: () => Xp,
  outerBind: () => Oh,
  outside: () => Bd,
  overgain: () => Ja,
  overshape: () => $a,
  pace: () => Vn,
  pairs: () => un,
  palindrome: () => Zd,
  pan: () => Na,
  panchor: () => ma,
  panorient: () => Fa,
  panspan: () => La,
  pansplay: () => Ra,
  panwidth: () => Wa,
  parray: () => me,
  parseFractional: () => cn,
  parseNumeral: () => ce,
  partials: () => my,
  patt: () => ca,
  pattack: () => oa,
  pcurve: () => da,
  pdec: () => ua,
  pdecay: () => ia,
  penv: () => ha,
  per: () => Df,
  perCycle: () => Fw,
  perlin: () => kw,
  perx: () => Iw,
  ph: () => ai,
  phasdp: () => wi,
  phaser: () => li,
  phasercenter: () => hi,
  phaserdepth: () => mi,
  phaserrate: () => ui,
  phasersweep: () => pi,
  phases: () => yy,
  phc: () => di,
  phd: () => yi,
  phs: () => fi,
  pick: () => yf,
  pickF: () => xy,
  pickOut: () => Oy,
  pickReset: () => Ey,
  pickRestart: () => My,
  pickSqueeze: () => $y,
  pickmod: () => gf,
  pickmodF: () => By,
  pickmodOut: () => zy,
  pickmodReset: () => jy,
  pickmodRestart: () => Py,
  pickmodSqueeze: () => Ly,
  pipe: () => on,
  pitchJump: () => gp,
  pitchJumpTime: () => bp,
  ply: () => kd,
  plyForEach: () => lm,
  plyWith: () => am,
  pm: () => _h,
  polyBind: () => Ph,
  polyTouch: () => Qp,
  polymeter: () => $t,
  polyrhythm: () => gh,
  postgain: () => nr,
  pow: () => Fh,
  pr: () => bh,
  prel: () => fa,
  prelease: () => pa,
  press: () => Yd,
  pressBy: () => Kd,
  progNum: () => Fp,
  psus: () => la,
  psustain: () => aa,
  pure: () => C,
  pw: () => oi,
  pwrate: () => ci,
  pwsweep: () => ii,
  rand: () => W,
  rand2: () => hw,
  randL: () => aw,
  randcat: () => bw,
  randrun: () => Nf,
  range: () => ld,
  range2: () => fd,
  rangex: () => pd,
  rarely: () => Ew,
  ratio: () => hd,
  rdim: () => sl,
  real: () => Gl,
  ref: () => ry,
  register: () => l,
  registerControl: () => c,
  registerMultiControl: () => V,
  reify: () => d,
  rel: () => Ac,
  release: () => Sc,
  removeUndefineds: () => lt,
  repeatCycles: () => dm,
  repl: () => Dy,
  replicate: () => Em,
  reset_state: () => df,
  reset_timelines: () => mf,
  resonance: () => $u,
  rev: () => Rn,
  revv: () => Xd,
  rfade: () => ol,
  rib: () => xm,
  ribbon: () => Cm,
  ring: () => Wl,
  ringdf: () => Il,
  ringf: () => Fl,
  rlp: () => el,
  room: () => Za,
  roomdim: () => nl,
  roomfade: () => rl,
  roomlp: () => tl,
  roomsize: () => ll,
  rotate: () => rn,
  round: () => od,
  rsize: () => hl,
  run: () => jf,
  s: () => us,
  s_add: () => Fm,
  s_alt: () => Nm,
  s_cat: () => $m,
  s_contract: () => Dm,
  s_expand: () => Vm,
  s_extend: () => Hm,
  s_polymeter: () => Lm,
  s_sub: () => Im,
  s_taper: () => Rm,
  s_taperlist: () => Wm,
  s_tour: () => Gm,
  s_zip: () => Qm,
  saw: () => qt,
  saw2: () => Se,
  scram: () => Yl,
  scramble: () => pw,
  scrub: () => Yp,
  seconds: () => cp,
  seed: () => fw,
  seg: () => Fd,
  segment: () => Wd,
  semitone: () => Va,
  seq: () => Nn,
  seqPLoop: () => qh,
  sequence: () => Q,
  sequenceP: () => En,
  set: () => Eh,
  setCpsFunc: () => _f,
  setIsStarted: () => qf,
  setPattern: () => vf,
  setStringParser: () => mh,
  setTime: () => ee,
  setTriggerFunc: () => kf,
  shape: () => dl,
  shrink: () => Zn,
  shrinklist: () => Yn,
  shuffle: () => lw,
  signal: () => j,
  silence: () => q,
  sine: () => Af,
  sine2: () => Te,
  sinefold: () => hy,
  size: () => pl,
  slice: () => ss,
  slide: () => Ia,
  slow: () => Td,
  slowChunk: () => wm,
  slowcat: () => Z,
  slowcatPrime: () => fe,
  slowchunk: () => ym,
  smear: () => Kl,
  soft: () => iy,
  sol2note: () => uh,
  someCycles: () => Mw,
  someCyclesBy: () => zw,
  sometimes: () => Ow,
  sometimesBy: () => Bw,
  songPtr: () => ip,
  sound: () => as,
  source: () => Qs,
  sparsity: () => Cd,
  speak: () => Vw,
  speed: () => ye,
  splice: () => Ym,
  splitAt: () => ue,
  spread: () => Zu,
  square: () => Tf,
  square2: () => Xy,
  squeeze: () => Ry,
  squeezeBind: () => zh,
  squiz: () => Tl,
  src: () => Us,
  stack: () => z,
  stackBy: () => vh,
  stackCentre: () => $n,
  stackLeft: () => jn,
  stackRight: () => Jn,
  steady: () => Gy,
  stepBind: () => Mh,
  stepalt: () => Dn,
  stepcat: () => $,
  steps: () => Um,
  stepsPerOctave: () => Ca,
  stretch: () => Sl,
  striate: () => Km,
  stringifyValues: () => ae,
  struct: () => Ah,
  strudelScope: () => le,
  stut: () => um,
  stutWith: () => om,
  stutwith: () => cm,
  sub: () => Nh,
  superimpose: () => Th,
  sus: () => qc,
  sustain: () => kc,
  sustainpedal: () => zl,
  swing: () => Vd,
  swingBy: () => Id,
  sysex: () => Ip,
  sysexdata: () => Hp,
  sysexid: () => Vp,
  sz: () => fl,
  take: () => Gn,
  time: () => ew,
  timeCat: () => ns,
  timecat: () => Jm,
  timeline: () => Cy,
  toBipolar: () => ud,
  tokenizeNote: () => Ue,
  tour: () => ts,
  transient: () => rf,
  trem: () => Fc,
  tremolo: () => Wc,
  tremolodepth: () => Vc,
  tremolophase: () => Dc,
  tremoloshape: () => Gc,
  tremoloskew: () => Hc,
  tremolosync: () => Ic,
  tri: () => Ky,
  tri2: () => Yy,
  triode: () => jl,
  tsdelay: () => Dl,
  uid: () => up,
  undegrade: () => xw,
  undegradeBy: () => Cw,
  unicodeToBase64: () => wn,
  uniq: () => ah,
  uniqsort: () => lh,
  uniqsortr: () => yn,
  unison: () => Yu,
  unit: () => Al,
  useRNG: () => cw,
  v: () => xu,
  val: () => ap,
  valueToMidi: () => Zf,
  vel: () => tr,
  velocity: () => Zs,
  vib: () => Tu,
  vibmod: () => Ou,
  vibrato: () => Cu,
  vmod: () => zu,
  voice: () => Ha,
  vowel: () => Cl,
  warp: () => Cs,
  warpatt: () => Os,
  warpattack: () => Bs,
  warpdc: () => Rs,
  warpdec: () => Ms,
  warpdecay: () => zs,
  warpdepth: () => Ns,
  warpenv: () => Ds,
  warpmode: () => Fs,
  warprate: () => $s,
  warprel: () => Js,
  warprelease: () => js,
  warpshape: () => Ls,
  warpskew: () => Ws,
  warpsus: () => Es,
  warpsustain: () => Ps,
  warpsync: () => Gs,
  waveloss: () => xl,
  wavetablePhaseRand: () => Hs,
  wavetablePosition: () => ps,
  wavetableWarp: () => xs,
  wavetableWarpMode: () => Is,
  wchoose: () => _w,
  wchooseCycles: () => If,
  when: () => Gd,
  whenKey: () => Lw,
  withSeed: () => Lf,
  withValue: () => Ch,
  within: () => Pm,
  worklet: () => wy,
  wrandcat: () => vw,
  wt: () => ls,
  wtatt: () => ds,
  wtattack: () => hs,
  wtdc: () => As,
  wtdec: () => ys,
  wtdecay: () => ms,
  wtdepth: () => qs,
  wtenv: () => fs,
  wtphaserand: () => Vs,
  wtrate: () => vs,
  wtrel: () => _s,
  wtrelease: () => bs,
  wtshape: () => Ss,
  wtskew: () => Ts,
  wtsus: () => gs,
  wtsustain: () => ws,
  wtsync: () => ks,
  xfade: () => rs,
  xsdelay: () => Hl,
  zcrush: () => kp,
  zdelay: () => qp,
  zip: () => es,
  zipWith: () => Pt,
  zmod: () => vp,
  znoise: () => _p,
  zoom: () => Jd,
  zoomArc: () => $d,
  zoomarc: () => Nd,
  zrand: () => mp,
  zzfx: () => Sp
});
function zt(t, e = "cyclist") {
  process.env.NODE_ENV === "development" && console.error(t), E(`[${e}] error: ${t.message}`);
}
function E(t, e, n = {}) {
  let s = performance.now();
  Ut === t && s - Xt < Qe || (Ut = t, Xt = s, console.log(`%c${t}`, "background-color: black;color:white;border-radius:15px"), typeof document < "u" && typeof CustomEvent < "u" && document.dispatchEvent(
    new CustomEvent(oe, {
      detail: {
        message: t,
        type: e,
        data: n
      }
    })
  ));
}
function sn(t, e = 0) {
  return isNaN(Number(t)) ? (E(`"${t}" is not a number, falling back to ${e}`, "warning"), e) : t;
}
function w(t, e, n = t.length) {
  const s = function r(...o) {
    if (o.length >= n)
      return t.apply(this, o);
    {
      const i = function(...a) {
        return r.apply(this, o.concat(a));
      };
      return e && e(i, o), i;
    }
  };
  return e && e(s, []), s;
}
function ce(t) {
  const e = Number(t);
  if (!isNaN(e))
    return e;
  if (Mt(t))
    return gt(t);
  throw new Error(`cannot parse as numeral: "${t}"`);
}
function ie(t, e) {
  return (...n) => t(...n.map(e));
}
function L(t) {
  return ie(t, ce);
}
function cn(t) {
  const e = Number(t);
  if (!isNaN(e))
    return e;
  const n = {
    pi: Math.PI,
    w: 1,
    h: 0.5,
    q: 0.25,
    e: 0.125,
    s: 0.0625,
    t: 1 / 3,
    f: 0.2,
    x: 1 / 6
  }[t];
  if (typeof n < "u")
    return n;
  throw new Error(`cannot parse as fractional: "${t}"`);
}
function ah(t) {
  var e = {};
  return t.filter(function(n) {
    return e.hasOwn(n) ? false : e[n] = true;
  });
}
function lh(t) {
  return t.sort().filter(function(e, n, s) {
    return !n || e != s[n - 1];
  });
}
function yn(t) {
  return t.sort((e, n) => e.compare(n)).filter(function(e, n, s) {
    return !n || e.ne(s[n - 1]);
  });
}
function wn(t) {
  const e = new TextEncoder().encode(t);
  return btoa(String.fromCharCode(...e));
}
function gn(t) {
  const e = new Uint8Array(
    atob(t).split("").map((s) => s.charCodeAt(0))
  );
  return new TextDecoder().decode(e);
}
function ph(t) {
  return encodeURIComponent(wn(t));
}
function fh(t) {
  return gn(decodeURIComponent(t));
}
function bn(t, e) {
  return Array.isArray(t) ? t.map(e) : Object.fromEntries(Object.entries(t).map(([n, s], r) => [n, e(s, n, r)]));
}
function Kt(t, e) {
  return t / e;
}
function hh() {
  return performance.now() * 1e-3;
}
function vn() {
  return Date.now() * 1e-3;
}
function qn() {
  if (rt == null) {
    if (typeof window > "u")
      return;
    rt = {}, window.addEventListener("keydown", (t) => {
      rt[t.key] = true;
    }), window.addEventListener("keyup", (t) => {
      rt[t.key] = false;
    });
  }
  return { ...rt };
}
function ae(t, e = false) {
  return typeof t == "object" ? e ? JSON.stringify(t).slice(1, -1).replaceAll('"', "").replaceAll(",", " ") : JSON.stringify(t) : t;
}
function Tn(t, e, n) {
  if (e?.value !== void 0 && Object.keys(e).length === 1)
    return E("[warn]: Can't do arithmetic on control pattern."), t;
  const s = Object.keys(t).filter((r) => Object.keys(e).includes(r));
  return Object.assign({}, t, e, Object.fromEntries(s.map((r) => [r, n(t[r], e[r])])));
}
function Cn(t, e = 60) {
  let n = 0, s = m(0), r = [""], o = "";
  for (; r[0].length < e; ) {
    const i = t.queryArc(n, n + 1), a = i.filter((h) => h.hasOnset()).map((h) => h.duration), u = Sn(...a), p = u.inverse();
    r = r.map((h) => h + "|"), o += "|";
    for (let h = 0; h < p; h++) {
      const [y, g] = [s, s.add(u)], v = i.filter((O) => O.whole.begin.lte(y) && O.whole.end.gte(g)), _ = v.length - r.length;
      _ > 0 && (r = r.concat(Array(_).fill(o))), r = r.map((O, A) => {
        const I = v[A];
        if (I) {
          const P2 = I.whole.begin.eq(y) ? "" + I.value : "-";
          return O + P2;
        }
        return O + ".";
      }), o += ".", s = s.add(u);
    }
    n++;
  }
  return r.join(`
`);
}
function Bn(t, e = {}) {
  const { wrapExpression: n = true, wrapAsync: s = true } = e;
  n && (t = `{${t}}`), s && (t = `(async ()=>${t})()`);
  const r = `"use strict";return (${t})`;
  return Function(r)();
}
function zn(t, e) {
  let n = [];
  return e.forEach((s) => {
    const r = n.findIndex(([o]) => t(s, o));
    r === -1 ? n.push([s]) : n[r].push(s);
  }), n;
}
function dt(t) {
  return !Array.isArray(t) && typeof t == "object" && !An(t);
}
function Pn(t, e, n) {
  return dt(t) || dt(e) ? (dt(t) || (t = { value: t }), dt(e) || (e = { value: e }), Tn(t, e, n)) : n(t, e);
}
function C(t) {
  function e(s) {
    return s.span.spanCycles.map((r) => new S(m(r.begin).wholeCycle(), r, t));
  }
  const n = new f(e, 1);
  return n.__pure = t, n;
}
function pe(t) {
  return t instanceof f || t?._Pattern;
}
function d(t) {
  return pe(t) ? t : Ct && typeof t == "string" ? Ct(t) : C(t);
}
function En(t) {
  let e = C([]);
  for (const n of t)
    e = e.bind((s) => n.fmap((r) => s.concat([r])));
  return e;
}
function z(...t) {
  t = t.map((s) => Array.isArray(s) ? Q(...s) : d(s));
  const e = (s) => G(t.map((r) => r.query(s))), n = new f(e);
  return J && (n._steps = Y(...t.map((s) => s._steps))), n;
}
function Et(t, e) {
  if (e = e.map((o) => Array.isArray(o) ? Q(...o) : d(o)), e.length === 0)
    return q;
  if (e.length === 1)
    return e[0];
  const [n, ...s] = e.map((o) => o._steps), r = J ? n.maximum(...s) : void 0;
  return z(...t(r, e));
}
function jn(...t) {
  return Et(
    (e, n) => n.map((s) => s._steps.eq(e) ? s : $(s, pt(e.sub(s._steps)))),
    t
  );
}
function Jn(...t) {
  return Et(
    (e, n) => n.map((s) => s._steps.eq(e) ? s : $(pt(e.sub(s._steps)), s)),
    t
  );
}
function $n(...t) {
  return Et(
    (e, n) => n.map((s) => {
      if (s._steps.eq(e))
        return s;
      const r = pt(e.sub(s._steps).div(2));
      return $(r, s, r);
    }),
    t
  );
}
function vh(t, ...e) {
  const [n, ...s] = e.map((i) => i._steps), r = n.maximum(...s), o = {
    centre: $n,
    left: jn,
    right: Jn,
    expand: z,
    repeat: (...i) => $t(...i).steps(r)
  };
  return t.inhabit(o).fmap((i) => i(...e)).innerJoin().setSteps(r);
}
function Z(...t) {
  if (t = t.map((s) => Array.isArray(s) ? N(...s) : d(s)), t.length == 1)
    return t[0];
  const e = function(s) {
    const r = s.span, o = bt(r.begin.sam(), t.length), i = t[o];
    if (!i)
      return [];
    const a = r.begin.floor().sub(r.begin.div(t.length).floor());
    return i.withHapTime((u) => u.add(a)).query(s.setSpan(r.withTime((u) => u.sub(a))));
  }, n = J ? Y(...t.map((s) => s._steps)) : void 0;
  return new f(e).splitQueries().setSteps(n);
}
function fe(...t) {
  t = t.map(d);
  const e = function(n) {
    const s = Math.floor(n.span.begin) % t.length;
    return t[s]?.query(n) || [];
  };
  return new f(e).splitQueries();
}
function mt(...t) {
  return Z(...t);
}
function kh(...t) {
  const e = t.reduce((n, [s]) => n + s, 0);
  return t = t.map(([n, s]) => [n, s.fast(n)]), $(...t).slow(e);
}
function qh(...t) {
  let e = m(0);
  for (let n of t)
    n.length == 2 && n.unshift(e), e = n[1];
  return z(
    ...t.map(
      ([n, s, r]) => C(d(r)).compress(m(n).div(e), m(s).div(e))
    )
  ).slow(e).innerJoin();
}
function N(...t) {
  let e = Z(...t);
  return t.length > 1 && (e = e._fast(t.length), e._steps = t.length), t.length == 1 && t[0].__steps_source && (t._steps = t[0]._steps), e;
}
function Q(...t) {
  return N(...t);
}
function Nn(...t) {
  return N(...t);
}
function xt(t) {
  return Array.isArray(t) ? t.length == 0 ? [q, 0] : t.length == 1 ? xt(t[0]) : [N(...t.map((e) => xt(e)[0])), t.length] : [d(t), 1];
}
function l(t, e, n = true, s = false, r = (o) => o.innerJoin()) {
  if (Array.isArray(t)) {
    const u = {};
    for (const p of t)
      u[p] = l(p, e, n, s, r);
    return u;
  }
  const o = e.length;
  var i;
  n ? i = function(...u) {
    u = u.map(d);
    const p = u[u.length - 1];
    let h;
    if (o === 1)
      h = e(p);
    else {
      const y = u.slice(0, -1);
      if (y.every((g) => g.__pure != null)) {
        const g = y.map((_) => _.__pure), v = y.filter((_) => _.__pure_loc).map((_) => _.__pure_loc);
        h = e(...g, p), h = h.withContext((_) => {
          const O = (_.locations || []).concat(v);
          return { ..._, locations: O };
        });
      } else {
        const [g, ...v] = y;
        let _ = (...O) => e(...O, p);
        _ = w(_, null, o - 1), h = r(v.reduce((O, A) => O.appLeft(A), g.fmap(_)));
      }
    }
    return s && (h._steps = p._steps), h;
  } : i = function(...u) {
    u = u.map(d);
    const p = e(...u);
    return s && (p._steps = u[u.length - 1]._steps), p;
  }, f.prototype[t] = function(...u) {
    if (o === 2 && u.length !== 1)
      u = [Q(...u)];
    else if (o !== u.length + 1)
      throw new Error(`.${t}() expects ${o - 1} inputs but got ${u.length}.`);
    return u = u.map(d), i(...u, this);
  }, o > 1 && (f.prototype["_" + t] = function(...u) {
    const p = e(...u, this);
    return s && p.setSteps(this._steps), p;
  });
  const a = w(i, null, o);
  return le[t] = a, a;
}
function et(t, e, n = true, s = false, r = (o) => o.stepJoin()) {
  return l(t, e, n, s, r);
}
function Yt(t) {
  const e = t.filter((o, i) => i.hasSteps).reduce((o, i) => o.add(i), m(0)), n = lt(t.map((o, i) => i._steps)).reduce(
    (o, i) => o.add(i),
    m(0)
  ), s = e.eq(0) ? void 0 : n.div(e);
  function r(o, i) {
    return i._steps === void 0 ? [o.mulmaybe(s), i] : [i._steps, i];
  }
  return t.map((o) => r(...o));
}
function Zt(t) {
  const e = G(t.map((r) => [r.part.begin, r.part.end])), n = yn([m(0), m(1), ...e]);
  return un(n).map((r) => [
    r[1].sub(r[0]),
    z(...Fn(new B(...r), t).map((o) => o.value.withHap((i) => i.setContext(i.combineContext(o)))))
  ]);
}
function Fn(t, e) {
  return lt(e.map((n) => In(t, n)));
}
function In(t, e) {
  const n = t.intersection(e.part);
  if (n != null)
    return new S(e.whole, n, e.value, e.context);
}
function Hn(t, ...e) {
  const n = e.map((r) => xt(r));
  if (n.length == 0)
    return q;
  t == 0 && (t = n[0][1]);
  const s = [];
  for (const r of n)
    r[1] != 0 && (t == r[1] ? s.push(r[0]) : s.push(r[0]._fast(m(t).div(m(r[1])))));
  return z(...s);
}
function $t(...t) {
  if (Array.isArray(t[0]))
    return Hn(0, ...t);
  if (t = t.filter((s) => s.hasSteps), t.length == 0)
    return q;
  const e = Y(...t.map((s) => s._steps));
  if (e.eq(m(0)))
    return R;
  const n = z(...t.map((s) => s.pace(e)));
  return n._steps = e, n;
}
function $(...t) {
  if (t.length === 0)
    return R;
  const e = (i) => Array.isArray(i) ? i : [i._steps ?? 1, i];
  if (t = t.map(e), t.find((i) => i[0] === void 0)) {
    const i = t.map((u) => u[0]).filter((u) => u !== void 0);
    if (i.length === 0)
      return N(...t.map((u) => u[1]));
    if (i.length === t.length)
      return R;
    const a = i.reduce((u, p) => u.add(p), m(0)).div(i.length);
    for (let u of t)
      u[0] === void 0 && (u[0] = a);
  }
  if (t.length == 1)
    return d(t[0][1]).withSteps((a) => t[0][0]);
  const n = t.map((i) => i[0]).reduce((i, a) => i.add(a), m(0));
  let s = m(0);
  const r = [];
  for (const [i, a] of t) {
    if (m(i).eq(0))
      continue;
    const u = s.add(i);
    r.push(d(a)._compress(s.div(n), u.div(n))), s = u;
  }
  const o = z(...r);
  return o._steps = n, o;
}
function Dn(...t) {
  t = t.map((r) => Array.isArray(r) ? r.map(d) : [d(r)]);
  const e = Y(...t.map((r) => m(r.length)));
  let n = [];
  for (let r = 0; r < e; ++r)
    n.push(...t.map((o) => o.length == 0 ? q : o[r % o.length]));
  n = n.filter((r) => r.hasSteps && r._steps > 0);
  const s = n.reduce((r, o) => r.add(o._steps), m(0));
  return n = $(...n), n._steps = s, n;
}
function Nt(t) {
  let e = Array.isArray(t);
  t = e ? t : [t];
  const n = t[0], s = (o) => {
    let i;
    if (typeof o == "object" && o.value !== void 0 && (i = { ...o }, o = o.value, delete i.value), e && Array.isArray(o)) {
      const a = i || {};
      return o.forEach((u, p) => {
        p < t.length && (a[t[p]] = u);
      }), a;
    } else return i ? (i[n] = o, i) : { [n]: o };
  }, r = function(o, i) {
    return i ? typeof o > "u" ? i.fmap(s) : i.set(d(o).withValue(s)) : d(o).withValue(s);
  };
  return f.prototype[n] = function(o) {
    return r(o, this);
  }, r;
}
function is(t) {
  return at.has(t);
}
function c(t, ...e) {
  const n = Array.isArray(t) ? t[0] : t;
  let s = {};
  return s[n] = Nt(t), at.set(n, n), e.forEach((r) => {
    s[r] = s[n], at.set(r, n), f.prototype[r] = f.prototype[n];
  }), s;
}
function V(t, e, ...n) {
  t = Array.isArray(t) ? t : [t];
  let s = {};
  for (let r = 1; r <= e; r++) {
    let o = [...n], i = [...t];
    if (r === 1) {
      const u = o.map((h) => `${h}1`), p = i.map((h) => `${h}1`);
      o = o.concat(u).concat(p);
    } else
      o = o.map((u) => `${u}${r}`), i = i.map((u) => `${u}${r}`);
    const a = c(i, ...o);
    s = { ...s, ...a };
  }
  return s;
}
function ff(t, e, n = 0.05, s = 0.1, r = 0.1, o = globalThis.setInterval, i = globalThis.clearInterval, a = true) {
  let u = 0, p = 0, h = 10 ** 4, y = 0.01;
  const g = (x) => n = x(n);
  r = r || s / 2;
  const v = () => {
    const x = t(), D = x + s + r;
    for (p === 0 && (p = x + y); p < D; )
      p = a ? Math.round(p * h) / h : p, e(p, n, u, x), p += n, u++;
  };
  let _;
  const O = () => {
    A(), v(), _ = o(v, s * 1e3);
  }, A = () => {
    _ !== void 0 && i(_), _ = void 0;
  };
  return { setDuration: g, start: O, stop: () => {
    u = 0, p = 0, A();
  }, pause: () => A(), duration: n, interval: s, getPhase: () => p, minLatency: y };
}
function Wy() {
  if (!Ot)
    throw new Error("no time set! use setTime to define a time source");
  return Ot();
}
function ee(t) {
  Ot = t;
}
function _f(t) {
  _e = t;
}
function Fy() {
  return _e?.();
}
function vf(t) {
  ve = t;
}
function Iy() {
  return ve;
}
function kf(t) {
  ke = t;
}
function Vy() {
  return ke;
}
function qf(t) {
  qe = !!t;
}
function Hy() {
  return qe;
}
function Dy({
  defaultOutput: t,
  onEvalError: e,
  beforeEval: n,
  beforeStart: s,
  afterEval: r,
  getTime: o,
  transpiler: i,
  onToggle: a,
  editPattern: u,
  onUpdateState: p,
  sync: h = false,
  setInterval: y,
  clearInterval: g,
  id: v,
  mondo: _ = false
}) {
  const O = new (void 0)({ localScope: true }), A = {
    schedulerError: void 0,
    evalError: void 0,
    code: "// LOADING",
    activeCode: "// LOADING",
    pattern: void 0,
    miniLocations: [],
    widgets: [],
    pending: false,
    started: false
  }, I = {
    id: v
  }, H = (b) => {
    Object.assign(A, b), A.isDirty = A.code !== A.activeCode, A.error = A.evalError || A.schedulerError, p?.(A);
  }, P2 = {
    onTrigger: Sf({ defaultOutput: t, getTime: o }),
    getTime: o,
    onToggle: (b) => {
      H({ started: b }), qf(b), a?.(b), b || df();
    },
    setInterval: y,
    clearInterval: g,
    beforeStart: s
  }, x = h && typeof SharedWorker < "u" ? new bf(P2) : new hf(P2);
  kf(P2.onTrigger), _f(() => x.cps);
  let D = {}, nt = 0, tt;
  const Vt = function() {
    return D = {}, nt = 0, tt = void 0, q;
  }, Je = (b) => O.evaluate(b).compile({ log: false });
  function Ht(b) {
    return b._Pattern ? b.__pure : b;
  }
  const Dt = async (b, k = true) => (b = u?.(b) || b, await x.setPattern(b, k), vf(b), b);
  ee(() => x.now());
  const $e = () => x.stop(), Ne = () => x.start(), Le = () => x.pause(), Re = () => x.toggle(), St = (b) => (x.setCps(Ht(b)), q), Gt = (b) => (x.setCps(Ht(b) / 60), q);
  let ft = [];
  const We = function(b) {
    return ft.push(b), q;
  }, Fe = function(b) {
    return tt = b, q;
  }, Ie = () => {
    f.prototype.p = function(k) {
      return typeof k == "string" && (k.startsWith("_") || k.endsWith("_")) ? q : (k.includes("$") && (k = `${k}${nt}`, nt++), D[k] = this, this);
    }, f.prototype.q = function(k) {
      return q;
    };
    try {
      for (let k = 1; k < 10; ++k)
        Object.defineProperty(f.prototype, `d${k}`, {
          get() {
            return this.p(k);
          },
          configurable: true
        }), Object.defineProperty(f.prototype, `p${k}`, {
          get() {
            return this.p(k);
          },
          configurable: true
        }), f.prototype[`q${k}`] = q;
    } catch (k) {
      console.warn("injectPatternMethods: error:", k);
    }
    const b = l("cpm", function(k, At) {
      return At._fast(k / 60 / x.cps);
    });
    return xn({
      all: We,
      each: Fe,
      hush: Vt,
      cpm: b,
      setCps: St,
      setcps: St,
      setCpm: Gt,
      setcpm: Gt,
      compileKabel: Je
    });
  };
  return { scheduler: x, evaluate: async (b, k = true, At = true) => {
    if (!b)
      throw new Error("no code to evaluate");
    try {
      H({ code: b, pending: true }), await Ie(), ee(() => x.now()), await n?.({ code: b }), ft = [], At && Vt(), _ && (b = `mondolang\`${b}\``);
      let { pattern: M, meta: Tt } = await On(b, i, I);
      if (Object.keys(D).length) {
        let X = [], ht = false;
        for (const [st, Ve] of Object.entries(D)) {
          const Qt = st.length > 1 && st.startsWith("S");
          if (Qt && ht === false && (X = [], ht = true), !ht || ht && Qt) {
            const He = Ve.withState((De) => De.setControls({ id: st }));
            X.push(He);
          }
        }
        tt && (X = X.map((st) => tt(st))), M = z(...X);
      } else tt && (M = tt(M));
      if (ft.length)
        for (const X of ft)
          M = X(M);
      return pe(M) || (M = q), E("[eval] code updated"), M = await Dt(M, k), H({
        miniLocations: Tt?.miniLocations || [],
        widgets: Tt?.widgets || [],
        activeCode: b,
        pattern: M,
        evalError: void 0,
        schedulerError: void 0,
        pending: false
      }), r?.({ code: b, pattern: M, meta: Tt }), M;
    } catch (M) {
      E(`[eval] error: ${M.message}`, "error"), console.error(M), H({ evalError: M, pending: false }), e?.(M);
    }
  }, start: Ne, stop: $e, pause: Le, setCps: St, setPattern: Dt, setCode: (b) => H({ code: b }), toggle: Re, state: A };
}
function Gy(t) {
  return new f((e) => [new S(void 0, e.span, t)]);
}
function Vf(t, e = 0) {
  let n = Math.floor(t), s = n + 1;
  const r = (p) => 6 * p ** 5 - 15 * p ** 4 + 10 * p ** 3, o = (p) => (h) => (y) => h + r(p) * (y - h), i = K(n, 1, e), a = K(s, 1, e);
  return o(t - n)(i)(a);
}
function Hf(t, e = 0) {
  const n = Math.floor(t), s = n + 1, r = K(n, 1, e), o = K(s, 1, e), i = r + o, a = (t - n) / (s - n);
  return ((p, h, y) => p + y * (h - p))(r, i, a) / 2;
}
function je(t) {
  Array.isArray(t) === false && (t = [t]);
  const e = qn();
  return t.every((n) => {
    const s = kn.get(n) ?? n;
    return e[s];
  });
}
function Gf(t, e, n) {
  wt.cancel();
  const s = new SpeechSynthesisUtterance(t);
  s.lang = e, re = wt.getVoices();
  const r = re.filter((o) => o.lang.includes(e));
  typeof n == "number" ? s.voice = r[n % r.length] : typeof n == "string" && (s.voice = r.find((o) => o.name === o)), speechSynthesis.speak(s);
}
var oe, Qe, Ut, Xt, Yf, Mt, Ue, Xe, Ke, Ye, gt, it, Ze, Zf, th, tn, en, eh, bt, nn, nh, sh, rh, rn, on, oh, lt, G, ot, ch, _t, ih, ue, Pt, un, an, ln, pn, fn, hn, dn, mn, uh, _n, kn, rt, m, Sn, Y, An, B, S, ut, le, xn, On, Ct, J, dh, mh, f, Mn, yh, wh, gh, bh, _h, pt, q, R, Sh, Ah, Th, Ch, xh, Bh, Oh, zh, Mh, Ph, Eh, jh, Jh, $h, Nh, Lh, Rh, Wh, Fh, Ih, Vh, Hh, Dh, Gh, Qh, Uh, Xh, Kh, Yh, Zh, td, ed, nd, sd, rd, od, cd, id, ud, ad, ld, pd, fd, hd, dd, md, yd, wd, gd, bd, _d, vd, kd, qd, Sd, Ad, Td, Cd, xd, Bd, Od, zd, Md, Pd, Ed, jd, Ln, Jd, $d, Nd, Ld, Rd, Wd, Fd, Id, Vd, Hd, Dd, Gd, Qd, Ud, Rn, Xd, Kd, Yd, Zd, tm, em, nm, sm, rm, om, cm, im, um, Wn, am, lm, jt, pm, fm, hm, dm, Jt, mm, ym, wm, gm, bm, _m, vm, km, qm, Sm, Am, Tm, Cm, xm, Bm, Om, zm, Mm, Pm, Vn, Gn, Qn, Un, Em, Xn, Kn, Yn, Zn, jm, ts, es, Jm, ns, $m, Nm, Lm, Rm, Wm, Fm, Im, Vm, Hm, Dm, Gm, Qm, Um, Xm, Km, he, ss, Ym, Zm, ty, ey, ny, sy, ry, te, rs, os, oy, de, cy, U, iy, uy, ay, ly, py, fy, hy, dy, me, vt, my, yy, cs, wy, at, us, as, ls, ps, fs, hs, ds, ms, ys, ws, gs, bs, _s, vs, ks, qs, Ss, As, Ts, Cs, xs, Bs, Os, zs, Ms, Ps, Es, js, Js, $s, Ns, Ls, Rs, Ws, Fs, Is, Vs, Hs, Ds, Gs, Qs, Us, Xs, Ks, Ys, Zs, tr, er, nr, sr, rr, or, cr, ir, ur, ar, lr, pr, fr, hr, dr, mr, yr, wr, gr, br, _r, vr, kr, qr, Sr, Ar, Tr, Cr, xr, Br, Or, zr, Mr, Pr, Er, jr, Jr, $r, Nr, Lr, Rr, Wr, Fr, Ir, Vr, Hr, Dr, Gr, Qr, Ur, Xr, Kr, Yr, Zr, to, eo, no, so, ro, oo, co, io, uo, ao, lo, po, fo, ho, mo, yo, wo, go, bo, _o, vo, ko, qo, So, Ao, To, Co, xo, Bo, Oo, zo, Mo, Po, Eo, jo, Jo, $o, No, Lo, Ro, Wo, Fo, Io, Vo, Ho, Do, Go, Qo, Uo, Xo, Ko, Yo, Zo, tc, ec, nc, sc, rc, oc, cc, ic, uc, ac, lc, pc, fc, hc, dc, mc, yc, wc, gc, bc, _c, vc, kc, qc, Sc, Ac, Tc, Cc, xc, Bc, Oc, zc, Mc, Pc, Ec, jc, Jc, $c, Nc, Lc, Rc, Wc, Fc, Ic, Vc, Hc, Dc, Gc, Qc, Uc, Xc, Kc, Yc, Zc, ti, ei, ni, si, ri, oi, ci, ii, ui, ai, li, pi, fi, hi, di, mi, yi, wi, gi, bi, _i, vi, ki, qi, Si, Ai, Ti, Ci, xi, Bi, Oi, zi, Mi, Pi, Ei, ji, Ji, $i, Ni, Li, Ri, Wi, Fi, Ii, Vi, Hi, Di, Gi, Qi, Ui, Xi, Ki, Yi, Zi, tu, eu, nu, su, ru, ou, cu, iu, uu, au, lu, pu, fu, hu, du, mu, yu, wu, gu, bu, _u, vu, ku, qu, Su, Au, Tu, Cu, xu, Bu, Ou, zu, Mu, Pu, Eu, ju, Ju, $u, Nu, Lu, Ru, Wu, Fu, Iu, Vu, Hu, Du, Gu, Qu, Uu, Xu, Ku, Yu, Zu, ta, ea, na, sa, ra, oa, ca, ia, ua, aa, la, pa, fa, ha, da, ma, ya, wa, ga, ba, _a, va, ka, qa, Sa, Aa, Ta, Ca, xa, Ba, Oa, za, Ma, Pa, Ea, ja, Ja, $a, Na, La, Ra, Wa, Fa, Ia, Va, Ha, Da, Ga, Qa, Ua, Xa, Ka, Ya, Za, tl, el, nl, sl, rl, ol, cl, il, ul, al, ll, pl, fl, hl, dl, ml, yl, wl, gl, bl, _l, vl, kl, ql, ye, Sl, Al, Tl, Cl, xl, Bl, Ol, zl, Ml, Pl, El, jl, Jl, $l, Nl, Ll, Rl, Wl, Fl, Il, Vl, Hl, Dl, Gl, Ql, Ul, Xl, Kl, Yl, Zl, tp, ep, np, sp, rp, op, cp, ip, up, ap, lp, pp, fp, hp, dp, mp, yp, wp, gp, bp, _p, vp, kp, qp, Sp, Ap, Tp, Cp, xp, Bp, Op, zp, Mp, Pp, Ep, jp, Jp, $p, Np, Lp, Rp, Wp, Fp, Ip, Vp, Hp, Dp, Gp, Qp, Up, Xp, yt, Kp, Yp, Bt, Zp, Lt, tf, ef, nf, sf, rf, of, cf, uf, af, gy, lf, pf, we, ge, kt, by, _y, vy, ky, be, qy, Sy, Ay, Ty, hf, ct, df, mf, Cy, F, yf, wf, gf, xy, By, Oy, zy, My, Py, Ey, jy, Jy, $y, Ny, Ly, Ry, bf, Ot, _e, ve, ke, qe, Sf, j, qt, Se, Rt, Ae, Te, Af, Qy, Uy, Tf, Xy, Ky, Yy, Zy, tw, ew, Wt, Ft, nw, sw, rw, ow, Cf, xf, Bf, ne, Of, Ce, zf, Mf, se, Pf, Ef, xe, K, cw, jf, iw, Jf, uw, $f, aw, Nf, Be, lw, pw, Lf, fw, W, hw, Oe, dw, mw, ze, yw, Me, It, Pe, Rf, ww, gw, Wf, bw, Ee, Ff, _w, If, vw, kw, qw, Sw, Aw, Tw, Cw, xw, Bw, Ow, zw, Mw, Pw, Ew, jw, Jw, $w, Nw, Lw, Rw, Ww, Df, Fw, Iw, wt, re, Vw, Hw, Dw;
var init_dist2 = __esm({
  "outputs/skycam/labs/strudel/node_modules/@strudel/core/dist/index.mjs"() {
    init_fraction();
    init_dist();
    oe = "strudel.log";
    Qe = 1e3;
    E.key = oe;
    Yf = (t) => /^[a-gA-G][#bsf]*[0-9]*$/.test(t);
    Mt = (t) => /^[a-gA-G][#bsf]*-?[0-9]*$/.test(t);
    Ue = (t) => {
      if (typeof t != "string")
        return [];
      const [e, n = "", s] = t.match(/^([a-gA-G])([#bsf]*)(-?[0-9]*)$/)?.slice(1) || [];
      return e ? [e, n, s ? Number(s) : void 0] : [];
    };
    Xe = { c: 0, d: 2, e: 4, f: 5, g: 7, a: 9, b: 11 };
    Ke = { "#": 1, b: -1, s: 1, f: -1 };
    Ye = (t) => t?.split("").reduce((e, n) => e + Ke[n], 0) || 0;
    gt = (t, e = 3) => {
      const [n, s, r = e] = Ue(t);
      if (!n)
        throw new Error('not a note: "' + t + '"');
      const o = Xe[n.toLowerCase()], i = Ye(s);
      return (Number(r) + 1) * 12 + o + i;
    };
    it = (t) => Math.pow(2, (t - 69) / 12) * 440;
    Ze = (t) => 12 * Math.log(t / 440) / Math.LN2 + 69;
    Zf = (t, e) => {
      if (typeof t != "object")
        throw new Error("valueToMidi: expected object value");
      let { freq: n, note: s } = t;
      if (typeof n == "number")
        return Ze(n);
      if (typeof s == "string")
        return gt(s);
      if (typeof s == "number")
        return s;
      if (!e)
        throw new Error("valueToMidi: expected freq or note to be set");
      return e;
    };
    th = (t, e) => (t - e) * 1e3;
    tn = (t) => it(typeof t == "number" ? t : gt(t));
    en = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
    eh = (t) => {
      const e = Math.floor(t / 12) - 1;
      return en[t % 12] + e;
    };
    bt = (t, e) => (t % e + e) % e;
    nn = (t) => t.reduce((e, n) => e + n) / t.length;
    nh = (t, e) => bt(Math.round(sn(t ?? 0, 0)), e);
    sh = (t) => {
      let { value: e, context: n } = t, s = e;
      if (typeof s == "object" && !Array.isArray(s) && (s = s.note || s.n || s.value, s === void 0))
        throw new Error(`cannot find a playable note for ${JSON.stringify(e)}`);
      if (typeof s == "number" && n.type !== "frequency")
        s = it(t.value);
      else if (typeof s == "number" && n.type === "frequency")
        s = t.value;
      else if (typeof s != "string" || !Mt(s))
        throw new Error("not a note: " + JSON.stringify(s));
      return s;
    };
    rh = (t) => {
      let { value: e, context: n } = t;
      if (typeof e == "object")
        return e.freq ? e.freq : tn(e.note || e.n || e.value);
      if (typeof e == "number" && n.type !== "frequency")
        e = it(t.value);
      else if (typeof e == "string" && Mt(e))
        e = it(gt(t.value));
      else if (typeof e != "number")
        throw new Error("not a note or frequency: " + e);
      return e;
    };
    rn = (t, e) => t.slice(e).concat(t.slice(0, e));
    on = (...t) => t.reduce(
      (e, n) => (...s) => e(n(...s)),
      (e) => e
    );
    oh = (...t) => on(...t.reverse());
    lt = (t) => t.filter((e) => e != null);
    G = (t) => [].concat(...t);
    ot = (t) => t;
    ch = (t, e) => t;
    _t = (t, e) => Array.from({ length: e - t + 1 }, (n, s) => s + t);
    ih = (t) => ie(t, cn);
    ue = function(t, e) {
      return [e.slice(0, t), e.slice(t)];
    };
    Pt = (t, e, n) => e.map((s, r) => t(s, n[r]));
    un = function(t) {
      const e = [];
      for (let n = 0; n < t.length - 1; ++n)
        e.push([t[n], t[n + 1]]);
      return e;
    };
    an = (t, e, n) => Math.min(Math.max(t, e), n);
    ln = ["Do", "Reb", "Re", "Mib", "Mi", "Fa", "Solb", "Sol", "Lab", "La", "Sib", "Si"];
    pn = [
      "Sa",
      "Re",
      "Ga",
      "Ma",
      "Pa",
      "Dha",
      "Ni"
    ];
    fn = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Hb", "H"];
    hn = [
      "Ni",
      "Pab",
      "Pa",
      "Voub",
      "Vou",
      "Ga",
      "Dib",
      "Di",
      "Keb",
      "Ke",
      "Zob",
      "Zo"
    ];
    dn = [
      "I",
      "Ro",
      "Ha",
      "Ni",
      "Ho",
      "He",
      "To"
    ];
    mn = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
    uh = (t, e = "letters") => {
      const s = (e === "solfeggio" ? ln : e === "indian" ? pn : e === "german" ? fn : e === "byzantine" ? hn : e === "japanese" ? dn : mn)[t % 12], r = Math.floor(t / 12) - 1;
      return s + r;
    };
    _n = class {
      constructor({
        getTargetClockTime: e = vn,
        weight: n = 16,
        offsetDelta: s = 5e-3,
        checkAfterTime: r = 2,
        resetAfterTime: o = 8
      }) {
        this.offsetTime, this.timeAtPrevOffsetSample, this.prevOffsetTimes = [], this.getTargetClockTime = e, this.weight = n, this.offsetDelta = s, this.checkAfterTime = r, this.resetAfterTime = o, this.reset = () => {
          this.prevOffsetTimes = [], this.offsetTime = null, this.timeAtPrevOffsetSample = null;
        };
      }
      calculateOffset(e) {
        const n = this.getTargetClockTime(), s = n - this.timeAtPrevOffsetSample, r = n - e;
        if (s > this.resetAfterTime && this.reset(), this.offsetTime == null && (this.offsetTime = r), this.prevOffsetTimes.push(r), this.prevOffsetTimes.length > this.weight && this.prevOffsetTimes.shift(), this.timeAtPrevOffsetSample == null || s > this.checkAfterTime) {
          this.timeAtPrevOffsetSample = n;
          const o = nn(this.prevOffsetTimes);
          Math.abs(o - this.offsetTime) > this.offsetDelta && (this.offsetTime = o);
        }
        return this.offsetTime;
      }
      calculateTimestamp(e, n) {
        return this.calculateOffset(e) + n;
      }
    };
    kn = /* @__PURE__ */ new Map([
      ["control", "Control"],
      ["ctrl", "Control"],
      ["alt", "Alt"],
      ["shift", "Shift"],
      ["down", "ArrowDown"],
      ["up", "ArrowUp"],
      ["left", "ArrowLeft"],
      ["right", "ArrowRight"]
    ]);
    Fraction.prototype.sam = function() {
      return this.floor();
    };
    Fraction.prototype.nextSam = function() {
      return this.sam().add(1);
    };
    Fraction.prototype.wholeCycle = function() {
      return new B(this.sam(), this.nextSam());
    };
    Fraction.prototype.cyclePos = function() {
      return this.sub(this.sam());
    };
    Fraction.prototype.lt = function(t) {
      return this.compare(t) < 0;
    };
    Fraction.prototype.gt = function(t) {
      return this.compare(t) > 0;
    };
    Fraction.prototype.lte = function(t) {
      return this.compare(t) <= 0;
    };
    Fraction.prototype.gte = function(t) {
      return this.compare(t) >= 0;
    };
    Fraction.prototype.eq = function(t) {
      return this.compare(t) == 0;
    };
    Fraction.prototype.ne = function(t) {
      return this.compare(t) != 0;
    };
    Fraction.prototype.max = function(t) {
      return this.gt(t) ? this : t;
    };
    Fraction.prototype.maximum = function(...t) {
      return t = t.map((e) => new Fraction(e)), t.reduce((e, n) => n.max(e), this);
    };
    Fraction.prototype.min = function(t) {
      return this.lt(t) ? this : t;
    };
    Fraction.prototype.mulmaybe = function(t) {
      return t !== void 0 ? this.mul(t) : void 0;
    };
    Fraction.prototype.divmaybe = function(t) {
      return t !== void 0 ? this.div(t) : void 0;
    };
    Fraction.prototype.addmaybe = function(t) {
      return t !== void 0 ? this.add(t) : void 0;
    };
    Fraction.prototype.submaybe = function(t) {
      return t !== void 0 ? this.sub(t) : void 0;
    };
    Fraction.prototype.show = function() {
      return this.s * this.n + "/" + this.d;
    };
    Fraction.prototype.or = function(t) {
      return this.eq(0) ? t : this;
    };
    m = (t) => Fraction(t);
    Sn = (...t) => {
      if (t = lt(t), t.length !== 0)
        return t.reduce((e, n) => e.gcd(n), m(1));
    };
    Y = (...t) => {
      if (t = lt(t), t.length === 0)
        return;
      const e = t.pop();
      return t.reduce(
        (n, s) => n === void 0 || s === void 0 ? void 0 : n.lcm(s),
        e
      );
    };
    An = (t) => t instanceof Fraction;
    m._original = Fraction;
    B = class _B {
      constructor(e, n) {
        this.begin = m(e), this.end = m(n);
      }
      get spanCycles() {
        const e = [];
        var n = this.begin;
        const s = this.end, r = s.sam();
        if (n.equals(s))
          return [new _B(n, s)];
        for (; s.gt(n); ) {
          if (n.sam().equals(r)) {
            e.push(new _B(n, this.end));
            break;
          }
          const o = n.nextSam();
          e.push(new _B(n, o)), n = o;
        }
        return e;
      }
      get duration() {
        return this.end.sub(this.begin);
      }
      cycleArc() {
        const e = this.begin.cyclePos(), n = e.add(this.duration);
        return new _B(e, n);
      }
      withTime(e) {
        return new _B(e(this.begin), e(this.end));
      }
      withEnd(e) {
        return new _B(this.begin, e(this.end));
      }
      withCycle(e) {
        const n = this.begin.sam(), s = n.add(e(this.begin.sub(n))), r = n.add(e(this.end.sub(n)));
        return new _B(s, r);
      }
      intersection(e) {
        const n = this.begin.max(e.begin), s = this.end.min(e.end);
        if (!n.gt(s) && !(n.equals(s) && (n.equals(this.end) && this.begin.lt(this.end) || n.equals(e.end) && e.begin.lt(e.end))))
          return new _B(n, s);
      }
      intersection_e(e) {
        const n = this.intersection(e);
        if (n == null)
          throw "TimeSpans do not intersect";
        return n;
      }
      midpoint() {
        return this.begin.add(this.duration.div(m(2)));
      }
      equals(e) {
        return this.begin.equals(e.begin) && this.end.equals(e.end);
      }
      show() {
        return this.begin.show() + " \u2192 " + this.end.show();
      }
    };
    S = class _S {
      /*
            Event class, representing a value active during the timespan
            'part'. This might be a fragment of an event, in which case the
            timespan will be smaller than the 'whole' timespan, otherwise the
            two timespans will be the same. The 'part' must never extend outside of the
            'whole'. If the event represents a continuously changing value
            then the whole will be returned as None, in which case the given
            value will have been sampled from the point halfway between the
            start and end of the 'part' timespan.
            The context is to store a list of source code locations causing the event.
      
            The word 'Event' is more or less a reserved word in javascript, hence this
            class is named called 'Hap'.
            */
      constructor(e, n, s, r = {}, o = false) {
        this.whole = e, this.part = n, this.value = s, this.context = r, this.stateful = o, o && console.assert(typeof this.value == "function", "Stateful values must be functions");
      }
      get duration() {
        let e;
        return typeof this.value?.duration == "number" ? e = m(this.value.duration) : e = this.whole.end.sub(this.whole.begin), typeof this.value?.clip == "number" ? e.mul(this.value.clip) : e;
      }
      get endClipped() {
        return this.whole.begin.add(this.duration);
      }
      isActive(e) {
        return this.whole.begin <= e && this.endClipped >= e;
      }
      isInPast(e) {
        return e > this.endClipped;
      }
      isInNearPast(e, n) {
        return n - e <= this.endClipped;
      }
      isInFuture(e) {
        return e < this.whole.begin;
      }
      isInNearFuture(e, n) {
        return n < this.whole.begin && n > this.whole.begin - e;
      }
      isWithinTime(e, n) {
        return this.whole.begin <= n && this.endClipped >= e;
      }
      wholeOrPart() {
        return this.whole ? this.whole : this.part;
      }
      withSpan(e) {
        const n = this.whole ? e(this.whole) : void 0;
        return new _S(n, e(this.part), this.value, this.context);
      }
      withValue(e) {
        return new _S(this.whole, this.part, e(this.value), this.context);
      }
      hasOnset() {
        return this.whole != null && this.whole.begin.equals(this.part.begin);
      }
      hasTag(e) {
        return this.context.tags?.includes(e);
      }
      resolveState(e) {
        if (this.stateful && this.hasOnset()) {
          console.log("stateful");
          const n = this.value, [s, r] = n(e);
          return [s, new _S(this.whole, this.part, r, this.context, false)];
        }
        return [e, this];
      }
      spanEquals(e) {
        return this.whole == null && e.whole == null || this.whole.equals(e.whole);
      }
      equals(e) {
        return this.spanEquals(e) && this.part.equals(e.part) && // TODO would == be better ??
        this.value === e.value;
      }
      show(e = false) {
        const n = typeof this.value == "object" ? e ? JSON.stringify(this.value).slice(1, -1).replaceAll('"', "").replaceAll(",", " ") : JSON.stringify(this.value) : this.value;
        var s = "";
        if (this.whole == null)
          s = "~" + this.part.show;
        else {
          var r = this.whole.begin.equals(this.part.begin) && this.whole.end.equals(this.part.end);
          this.whole.begin.equals(this.part.begin) || (s = this.whole.begin.show() + " \u21DC "), r || (s += "("), s += this.part.show(), r || (s += ")"), this.whole.end.equals(this.part.end) || (s += " \u21DD " + this.whole.end.show());
        }
        return "[ " + s + " | " + n + " ]";
      }
      showWhole(e = false) {
        return `${this.whole == null ? "~" : this.whole.show()}: ${ae(this.value, e)}`;
      }
      combineContext(e) {
        const n = this;
        return { ...n.context, ...e.context, locations: (n.context.locations || []).concat(e.context.locations || []) };
      }
      setContext(e) {
        return new _S(this.whole, this.part, this.value, e);
      }
      ensureObjectValue() {
        if (typeof this.value != "object")
          throw new Error(
            `expected hap.value to be an object, but got "${this.value}". Hint: append .note() or .s() to the end`,
            "error"
          );
      }
    };
    ut = class _ut {
      constructor(e, n = {}) {
        this.span = e, this.controls = n;
      }
      // Returns new State with different span
      setSpan(e) {
        return new _ut(e, this.controls);
      }
      withSpan(e) {
        return this.setSpan(e(this.span));
      }
      // Returns new State with added controls.
      setControls(e) {
        return new _ut(this.span, { ...this.controls, ...e });
      }
    };
    w((t, e) => t * e);
    w((t, e) => e.map(t));
    le = {};
    xn = async (...t) => {
      const e = await Promise.allSettled(t), n = e.filter((s) => s.status === "fulfilled").map((s) => s.value);
      return e.forEach((s, r) => {
        s.status === "rejected" && console.warn(`evalScope: module with index ${r} could not be loaded:`, s.reason);
      }), n.forEach((s) => {
        Object.entries(s).forEach(([r, o]) => {
          globalThis[r] = o, le[r] = o;
        });
      }), n;
    };
    On = async (t, e, n) => {
      let s = {};
      if (e) {
        const i = e(t, n);
        t = i.output, s = i;
      }
      return { mode: "javascript", pattern: await Bn(t, { wrapExpression: !!e }), meta: s };
    };
    J = true;
    dh = function(t) {
      J = !!t;
    };
    mh = (t) => Ct = t;
    f = class _f2 {
      /**
       * Create a pattern. As an end user, you will most likely not create a Pattern directly.
       *
       * @param {function} query - The function that maps a `State` to an array of `Hap`.
       * @noAutocomplete
       */
      constructor(e, n = void 0) {
        this.query = e, this._Pattern = true, this._steps = n;
      }
      get _steps() {
        return this.__steps;
      }
      set _steps(e) {
        this.__steps = e === void 0 ? void 0 : m(e);
      }
      setSteps(e) {
        return this._steps = e, this;
      }
      withSteps(e) {
        return J ? new _f2(this.query, this._steps === void 0 ? void 0 : e(this._steps)) : this;
      }
      get hasSteps() {
        return this._steps !== void 0;
      }
      //////////////////////////////////////////////////////////////////////
      // Haskell-style functor, applicative and monadic operations
      /**
       * Returns a new pattern, with the function applied to the value of
       * each hap. It has the alias `fmap`.
       * @synonyms fmap
       * @param {Function} func to to apply to the value
       * @returns Pattern
       * @example
       * "0 1 2".withValue(v => v + 10).log()
       */
      withValue(e) {
        const n = new _f2((s) => this.query(s).map((r) => r.withValue(e)));
        return n._steps = this._steps, n;
      }
      // runs func on query state
      withState(e) {
        return new _f2((n) => this.query(e(n)));
      }
      /**
       * see `withValue`
       * @noAutocomplete
       */
      fmap(e) {
        return this.withValue(e);
      }
      /**
       * Assumes 'this' is a pattern of functions, and given a function to
       * resolve wholes, applies a given pattern of values to that
       * pattern of functions.
       * @param {Function} whole_func
       * @param {Function} func
       * @noAutocomplete
       * @returns Pattern
       */
      appWhole(e, n) {
        const s = this, r = function(o) {
          const i = s.query(o), a = n.query(o), u = function(p, h) {
            const y = p.part.intersection(h.part);
            if (y != null)
              return new S(
                e(p.whole, h.whole),
                y,
                p.value(h.value),
                h.combineContext(p)
              );
          };
          return G(
            i.map((p) => lt(a.map((h) => u(p, h))))
          );
        };
        return new _f2(r);
      }
      /**
       * When this method is called on a pattern of functions, it matches its haps
       * with those in the given pattern of values.  A new pattern is returned, with
       * each matching value applied to the corresponding function.
       *
       * In this `_appBoth` variant, where timespans of the function and value haps
       * are not the same but do intersect, the resulting hap has a timespan of the
       * intersection. This applies to both the part and the whole timespan.
       * @param {Pattern} pat_val
       * @noAutocomplete
       * @returns Pattern
       */
      appBoth(e) {
        const n = this, s = function(o, i) {
          if (!(o == null || i == null))
            return o.intersection_e(i);
        }, r = n.appWhole(s, e);
        return J && (r._steps = Y(e._steps, n._steps)), r;
      }
      /**
       * As with `appBoth`, but the `whole` timespan is not the intersection,
       * but the timespan from the function of patterns that this method is called
       * on. In practice, this means that the pattern structure, including onsets,
       * are preserved from the pattern of functions (often referred to as the left
       * hand or inner pattern).
       * @param {Pattern} pat_val
       * @noAutocomplete
       * @returns Pattern
       */
      appLeft(e) {
        const n = this, s = function(o) {
          const i = [];
          for (const a of n.query(o)) {
            const u = e.query(o.setSpan(a.wholeOrPart()));
            for (const p of u) {
              const h = a.whole, y = a.part.intersection(p.part);
              if (y) {
                const g = a.value(p.value), v = p.combineContext(a), _ = new S(h, y, g, v);
                i.push(_);
              }
            }
          }
          return i;
        }, r = new _f2(s);
        return r._steps = this._steps, r;
      }
      /**
       * As with `appLeft`, but `whole` timespans are instead taken from the
       * pattern of values, i.e. structure is preserved from the right hand/outer
       * pattern.
       * @param {Pattern} pat_val
       * @noAutocomplete
       * @returns Pattern
       */
      appRight(e) {
        const n = this, s = function(o) {
          const i = [];
          for (const a of e.query(o)) {
            const u = n.query(o.setSpan(a.wholeOrPart()));
            for (const p of u) {
              const h = a.whole, y = p.part.intersection(a.part);
              if (y) {
                const g = p.value(a.value), v = a.combineContext(p), _ = new S(h, y, g, v);
                i.push(_);
              }
            }
          }
          return i;
        }, r = new _f2(s);
        return r._steps = e._steps, r;
      }
      bindWhole(e, n) {
        const s = this, r = function(o) {
          const i = function(u, p) {
            return new S(
              e(u.whole, p.whole),
              p.part,
              p.value,
              Object.assign({}, u.context, p.context, {
                locations: (u.context.locations || []).concat(p.context.locations || [])
              })
            );
          }, a = function(u) {
            return n(u.value).query(o.setSpan(u.part)).map((p) => i(u, p));
          };
          return G(s.query(o).map((u) => a(u)));
        };
        return new _f2(r);
      }
      bind(e) {
        const n = function(s, r) {
          if (!(s == null || r == null))
            return s.intersection_e(r);
        };
        return this.bindWhole(n, e);
      }
      join() {
        return this.bind(ot);
      }
      outerBind(e) {
        return this.bindWhole((n) => n, e).setSteps(this._steps);
      }
      outerJoin() {
        return this.outerBind(ot);
      }
      innerBind(e) {
        return this.bindWhole((n, s) => s, e);
      }
      innerJoin() {
        return this.innerBind(ot);
      }
      // Flatterns patterns of patterns, by retriggering/resetting inner patterns at onsets of outer pattern haps
      resetJoin(e = false) {
        const n = this;
        return new _f2((s) => n.discreteOnly().query(s).map((r) => r.value.late(e ? r.whole.begin : r.whole.begin.cyclePos()).query(s).map(
          (o) => new S(
            // Supports continuous haps in the inner pattern
            o.whole ? o.whole.intersection(r.whole) : void 0,
            o.part.intersection(r.part),
            o.value
          ).setContext(r.combineContext(o))
        ).filter((o) => o.part)).flat());
      }
      restartJoin() {
        return this.resetJoin(true);
      }
      // Like the other joins above, joins a pattern of patterns of values, into a flatter
      // pattern of values. In this case it takes whole cycles of the inner pattern to fit each event
      // in the outer pattern.
      squeezeJoin() {
        const e = this;
        function n(s) {
          const r = e.discreteOnly().query(s);
          function o(a) {
            const p = a.value._focusSpan(a.wholeOrPart()).query(s.setSpan(a.part));
            function h(y, g) {
              let v;
              if (g.whole && y.whole && (v = g.whole.intersection(y.whole), !v))
                return;
              const _ = g.part.intersection(y.part);
              if (!_)
                return;
              const O = g.combineContext(y);
              return new S(v, _, g.value, O);
            }
            return p.map((y) => h(a, y));
          }
          return G(r.map(o)).filter((a) => a);
        }
        return new _f2(n);
      }
      squeezeBind(e) {
        return this.fmap(e).squeezeJoin();
      }
      polyJoin = function() {
        const e = this;
        return e.fmap((n) => n.extend(e._steps.div(n._steps))).outerJoin();
      };
      polyBind(e) {
        return this.fmap(e).polyJoin();
      }
      //////////////////////////////////////////////////////////////////////
      // Utility methods mainly for internal use
      /**
       * Query haps inside the given time span.
       *
       * @param {Fraction | number} begin from time
       * @param {Fraction | number} end to time
       * @returns Hap[]
       * @example
       * const pattern = sequence('a', ['b', 'c'])
       * const haps = pattern.queryArc(0, 1)
       * console.log(haps)
       * silence
       * @noAutocomplete
       */
      queryArc(e, n, s = {}) {
        try {
          return this.query(new ut(new B(e, n), s));
        } catch (r) {
          return zt(r, "query"), [];
        }
      }
      /**
       * Returns a new pattern, with queries split at cycle boundaries. This makes
       * some calculations easier to express, as all haps are then constrained to
       * happen within a cycle.
       * @returns Pattern
       * @noAutocomplete
       */
      splitQueries() {
        const e = this, n = (s) => G(s.span.spanCycles.map((r) => e.query(s.setSpan(r))));
        return new _f2(n);
      }
      /**
       * Returns a new pattern, where the given function is applied to the query
       * timespan before passing it to the original pattern.
       * @param {Function} func the function to apply
       * @returns Pattern
       * @noAutocomplete
       */
      withQuerySpan(e) {
        return new _f2((n) => this.query(n.withSpan(e)));
      }
      withQuerySpanMaybe(e) {
        const n = this;
        return new _f2((s) => {
          const r = s.withSpan(e);
          return r.span ? n.query(r) : [];
        });
      }
      /**
       * As with `withQuerySpan`, but the function is applied to both the
       * begin and end time of the query timespan.
       * @param {Function} func the function to apply
       * @returns Pattern
       * @noAutocomplete
       */
      withQueryTime(e) {
        return new _f2((n) => this.query(n.withSpan((s) => s.withTime(e))));
      }
      /**
       * Similar to `withQuerySpan`, but the function is applied to the timespans
       * of all haps returned by pattern queries (both `part` timespans, and where
       * present, `whole` timespans).
       * @param {Function} func
       * @returns Pattern
       * @noAutocomplete
       */
      withHapSpan(e) {
        return new _f2((n) => this.query(n).map((s) => s.withSpan(e)));
      }
      /**
       * As with `withHapSpan`, but the function is applied to both the
       * begin and end time of the hap timespans.
       * @param {Function} func the function to apply
       * @returns Pattern
       * @noAutocomplete
       */
      withHapTime(e) {
        return this.withHapSpan((n) => n.withTime(e));
      }
      /**
       * Returns a new pattern with the given function applied to the list of haps returned by every query.
       * @param {Function} func
       * @returns Pattern
       * @noAutocomplete
       */
      withHaps(e) {
        const n = new _f2((s) => e(this.query(s), s));
        return n._steps = this._steps, n;
      }
      /**
       * As with `withHaps`, but applies the function to every hap, rather than every list of haps.
       * @param {Function} func
       * @returns Pattern
       * @noAutocomplete
       */
      withHap(e) {
        return this.withHaps((n) => n.map(e));
      }
      /**
       * Returns a new pattern with the context field set to every hap set to the given value.
       * @param {*} context
       * @returns Pattern
       * @noAutocomplete
       */
      setContext(e) {
        return this.withHap((n) => n.setContext(e));
      }
      /**
       * Returns a new pattern with the given function applied to the context field of every hap.
       * @param {Function} func
       * @returns Pattern
       * @noAutocomplete
       */
      withContext(e) {
        const n = this.withHap((s) => s.setContext(e(s.context)));
        return this.__pure !== void 0 && (n.__pure = this.__pure, n.__pure_loc = this.__pure_loc), n;
      }
      /**
       * Returns a new pattern with the context field of every hap set to an empty object.
       * @returns Pattern
       * @noAutocomplete
       */
      stripContext() {
        return this.withHap((e) => e.setContext({}));
      }
      /**
       * Returns a new pattern with the given location information added to the
       * context of every hap.
       * @param {Number} start start offset
       * @param {Number} end end offset
       * @returns Pattern
       * @noAutocomplete
       */
      withLoc(e, n) {
        const s = {
          start: e,
          end: n
        }, r = this.withContext((o) => {
          const i = (o.locations || []).concat([s]);
          return { ...o, locations: i };
        });
        return this.__pure && (r.__pure = this.__pure, r.__pure_loc = s), r;
      }
      /**
       * Returns a new Pattern, which only returns haps that meet the given test.
       * @param {Function} hap_test - a function which returns false for haps to be removed from the pattern
       * @returns Pattern
       * @example
       * s("bd*8").velocity(rand).filterHaps((h) => (h.whole.begin % 1) < h.value.velocity)
       */
      filterHaps(e) {
        return new _f2((n) => this.query(n).filter(e));
      }
      /**
       * As with `filterHaps`, but the function is applied to values
       * inside haps.
       * @param {Function} value_test
       * @returns Pattern
       * @example
       * const drums = s("bd sd bd sd")
       * kick: drums.filterValues((v) => v.s === 'bd').duck(2)
       * snare: drums.filterValues((v) => v.s === 'sd')
       * bass: s("saw!4").note("G#1").lpf(80).lpenv(4).orbit(2)
       */
      filterValues(e) {
        return new _f2((n) => this.query(n).filter((s) => e(s.value))).setSteps(this._steps);
      }
      /**
       * Returns a new pattern, with haps containing undefined values removed from
       * query results.
       * @returns Pattern
       * @noAutocomplete
       */
      removeUndefineds() {
        return this.filterValues((e) => e != null);
      }
      /**
       * Returns a new pattern, with all haps without onsets filtered out. A hap
       * with an onset is one with a `whole` timespan that begins at the same time
       * as its `part` timespan.
       * @returns Pattern
       * @noAutocomplete
       */
      onsetsOnly() {
        return this.filterHaps((e) => e.hasOnset());
      }
      /**
       * Returns a new pattern, with 'continuous' haps (those without 'whole'
       * timespans) removed from query results.
       * @returns Pattern
       * @noAutocomplete
       */
      discreteOnly() {
        return this.filterHaps((e) => e.whole);
      }
      /**
       * Combines adjacent haps with the same value and whole.  Only
       * intended for use in tests.
       * @noAutocomplete
       */
      defragmentHaps() {
        return this.discreteOnly().withHaps((n) => {
          const s = [];
          for (var r = 0; r < n.length; ++r) {
            for (var o = true, i = n[r]; o; ) {
              const p = JSON.stringify(n[r].value);
              for (var a = false, u = r + 1; u < n.length; u++) {
                const h = n[u];
                if (i.whole.equals(h.whole)) {
                  if (i.part.begin.eq(h.part.end)) {
                    if (p === JSON.stringify(h.value)) {
                      i = new S(i.whole, new B(h.part.begin, i.part.end), i.value), n.splice(u, 1), a = true;
                      break;
                    }
                  } else if (h.part.begin.eq(i.part.end) && p == JSON.stringify(h.value)) {
                    i = new S(i.whole, new B(i.part.begin, h.part.end), i.value), n.splice(u, 1), a = true;
                    break;
                  }
                }
              }
              o = a;
            }
            s.push(i);
          }
          return s;
        });
      }
      /**
       * Queries the pattern for the first cycle, returning Haps. Mainly of use when
       * debugging a pattern.
       * @param {Boolean} with_context - set to true, otherwise the context field
       * will be stripped from the resulting haps.
       * @returns [Hap]
       * @noAutocomplete
       */
      firstCycle(e = false) {
        var n = this;
        return e || (n = n.stripContext()), n.query(new ut(new B(m(0), m(1))));
      }
      /**
       * Accessor for a list of values returned by querying the first cycle.
       * @noAutocomplete
       */
      get firstCycleValues() {
        return this.firstCycle().map((e) => e.value);
      }
      /**
       * More human-readable version of the `firstCycleValues` accessor.
       * @noAutocomplete
       */
      get showFirstCycle() {
        return this.firstCycle().map(
          (e) => `${e.value}: ${e.whole.begin.toFraction()} - ${e.whole.end.toFraction()}`
        );
      }
      /**
       * Returns a new pattern, which returns haps sorted in temporal order. Mainly
       * of use when comparing two patterns for equality, in tests.
       * @returns Pattern
       * @noAutocomplete
       */
      sortHapsByPart() {
        return this.withHaps(
          (e) => e.sort(
            (n, s) => n.part.begin.sub(s.part.begin).or(n.part.end.sub(s.part.end)).or(n.whole.begin.sub(s.whole.begin).or(n.whole.end.sub(s.whole.end)))
          )
        );
      }
      asNumber() {
        return this.fmap(ce);
      }
      //////////////////////////////////////////////////////////////////////
      // Operators - see 'make composers' later..
      _opIn(e, n) {
        return this.fmap(n).appLeft(d(e));
      }
      _opOut(e, n) {
        return this.fmap(n).appRight(d(e));
      }
      _opMix(e, n) {
        return this.fmap(n).appBoth(d(e));
      }
      _opSqueeze(e, n) {
        const s = d(e);
        return this.fmap((r) => s.fmap((o) => n(r)(o))).squeezeJoin();
      }
      _opSqueezeOut(e, n) {
        const s = this;
        return d(e).fmap((o) => s.fmap((i) => n(i)(o))).squeezeJoin();
      }
      _opReset(e, n) {
        return d(e).fmap((r) => this.fmap((o) => n(o)(r))).resetJoin();
      }
      _opRestart(e, n) {
        return d(e).fmap((r) => this.fmap((o) => n(o)(r))).restartJoin();
      }
      _opPoly(e, n) {
        const s = d(e);
        return this.fmap((r) => s.fmap((o) => n(o)(r))).polyJoin();
      }
      //////////////////////////////////////////////////////////////////////
      // End-user methods.
      // Those beginning with an underscore (_) are 'patternified',
      // i.e. versions are created without the underscore, that are
      // magically transformed to accept patterns for all their arguments.
      //////////////////////////////////////////////////////////////////////
      // Methods without corresponding toplevel functions
      /**
       * Layers the result of the given function(s). Like `superimpose`, but without the original pattern:
       * @name layer
       * @memberof Pattern
       * @synonyms apply
       * @returns Pattern
       * @example
       * "<0 2 4 6 ~ 4 ~ 2 0!3 ~!5>*8"
       *   .layer(x=>x.add("0,2"))
       *   .scale('C minor').note()
       */
      layer(...e) {
        return z(...e.map((n) => n(this)));
      }
      /**
       * Superimposes the result of the given function(s) on top of the original pattern:
       * @name superimpose
       * @memberof Pattern
       * @returns Pattern
       * @example
       * "<0 2 4 6 ~ 4 ~ 2 0!3 ~!5>*8"
       *   .superimpose(x=>x.add(2))
       *   .scale('C minor').note()
       */
      superimpose(...e) {
        return this.stack(...e.map((n) => n(this)));
      }
      //////////////////////////////////////////////////////////////////////
      // Multi-pattern functions
      stack(...e) {
        return z(this, ...e);
      }
      sequence(...e) {
        return Q(this, ...e);
      }
      seq(...e) {
        return Q(this, ...e);
      }
      cat(...e) {
        return mt(this, ...e);
      }
      fastcat(...e) {
        return N(this, ...e);
      }
      slowcat(...e) {
        return Z(this, ...e);
      }
      //////////////////////////////////////////////////////////////////////
      // Context methods - ones that deal with metadata
      onTrigger(e, n = true) {
        return this.withHap(
          (s) => s.setContext({
            ...s.context,
            onTrigger: (...r) => {
              s.context.onTrigger?.(...r), e(...r);
            },
            // if dominantTrigger is set to true, the default output (webaudio) will be disabled
            // when using multiple triggers, you cannot flip this flag to false again!
            // example: x.csound('CooLSynth').log() as well as x.log().csound('CooLSynth') should work the same
            dominantTrigger: s.context.dominantTrigger || n
          })
        );
      }
      /**
       * Writes the content of the current event to the console (visible in the side menu).
       * @name log
       * @memberof Pattern
       * @example
       * s("bd sd").log()
       */
      log(e = (s) => `[hap] ${s.showWhole(true)}`, n = (s) => ({ hap: s })) {
        return this.onTrigger((...s) => {
          E(e(...s), void 0, n(...s));
        }, false);
      }
      /**
       * A simplified version of `log` which writes all "values" (various configurable parameters)
       * within the event to the console (visible in the side menu).
       * @name logValues
       * @memberof Pattern
       * @example
       * s("bd sd").gain("0.25 0.5 1").n("2 1 0").logValues()
       */
      logValues(e = (n) => `[hap] ${ae(n, true)}`) {
        return this.log((n) => e(n.value));
      }
      //////////////////////////////////////////////////////////////////////
      // Visualisation
      drawLine() {
        return console.log(Cn(this)), this;
      }
      //////////////////////////////////////////////////////////////////////
      // methods relating to breaking patterns into subcycles
      // Breaks a pattern into a pattern of patterns, according to the structure of the given binary pattern.
      unjoin(e, n = ot) {
        return e.withHap(
          (s) => s.withValue((r) => r ? n(this.ribbon(s.whole.begin, s.whole.duration)) : this)
        );
      }
      /**
       * Breaks a pattern into pieces according to the structure of a given pattern.
       * True values in the given pattern cause the corresponding subcycle of the
       * source pattern to be looped, and for an (optional) given function to be
       * applied. False values result in the corresponding part of the source pattern
       * to be played unchanged.
       * @name into
       * @memberof Pattern
       * @example
       * sound("bd sd ht lt").into("1 0", hurry(2))
       */
      into(e, n) {
        return this.unjoin(e, n).innerJoin();
      }
    };
    Mn = (t, e) => t.spanEquals(e);
    f.prototype.collect = function() {
      return this.withHaps(
        (t) => zn(Mn, t).map((e) => new S(e[0].whole, e[0].part, e, {}))
      );
    };
    yh = l("arpWith", (t, e) => e.collect().fmap((n) => d(t(n))).innerJoin().withHap((n) => new S(n.whole, n.part, n.value.value, n.combineContext(n.value))));
    wh = l(
      "arp",
      (t, e) => e.arpWith((n) => d(t).fmap((s) => n[s % n.length])),
      false
    );
    (function() {
      const t = {
        set: [(n, s) => s],
        keep: [(n) => n],
        keepif: [(n, s) => s ? n : void 0],
        // numerical functions
        /**
         *
         * Assumes a pattern of numbers. Adds the given number to each item in the pattern.
         * @name add
         * @memberof Pattern
         * @example
         * // Here, the triad 0, 2, 4 is shifted by different amounts
         * n("0 2 4".add("<0 3 4 0>")).scale("C:major")
         * // Without add, the equivalent would be:
         * // n("<[0 2 4] [3 5 7] [4 6 8] [0 2 4]>").scale("C:major")
         * @example
         * // You can also use add with notes:
         * note("c3 e3 g3".add("<0 5 7 0>"))
         * // Behind the scenes, the notes are converted to midi numbers:
         * // note("48 52 55".add("<0 5 7 0>"))
         */
        add: [L((n, s) => n + s)],
        // support string concatenation
        /**
         *
         * Like add, but the given numbers are subtracted.
         * @name sub
         * @memberof Pattern
         * @example
         * n("0 2 4".sub("<0 1 2 3>")).scale("C4:minor")
         * // See add for more information.
         */
        sub: [L((n, s) => n - s)],
        /**
         *
         * Multiplies each number by the given factor.
         * @name mul
         * @memberof Pattern
         * @example
         * "<1 1.5 [1.66, <2 2.33>]>*4".mul(150).freq()
         */
        mul: [L((n, s) => n * s)],
        /**
         *
         * Divides each number by the given factor.
         * @name div
         * @memberof Pattern
         */
        div: [L((n, s) => n / s)],
        mod: [L(bt)],
        pow: [L(Math.pow)],
        log2: [L(Math.log2)],
        band: [L((n, s) => n & s)],
        bor: [L((n, s) => n | s)],
        bxor: [L((n, s) => n ^ s)],
        blshift: [L((n, s) => n << s)],
        brshift: [L((n, s) => n >> s)],
        // TODO - force numerical comparison if both look like numbers?
        lt: [(n, s) => n < s],
        gt: [(n, s) => n > s],
        lte: [(n, s) => n <= s],
        gte: [(n, s) => n >= s],
        eq: [(n, s) => n == s],
        eqt: [(n, s) => n === s],
        ne: [(n, s) => n != s],
        net: [(n, s) => n !== s],
        and: [(n, s) => n && s],
        or: [(n, s) => n || s],
        //  bitwise ops
        func: [(n, s) => s(n)]
      }, e = ["In", "Out", "Mix", "Squeeze", "SqueezeOut", "Reset", "Restart", "Poly"];
      for (const [n, [s, r]] of Object.entries(t)) {
        f.prototype["_" + n] = function(o) {
          return this.fmap((i) => s(i, o));
        }, Object.defineProperty(f.prototype, n, {
          // a getter that returns a function, so 'pat' can be
          // accessed by closures that are methods of that function..
          get: function() {
            const o = this, i = (...a) => o[n].in(...a);
            for (const a of e)
              i[a.toLowerCase()] = function(...u) {
                var p = o;
                u = Q(u), r && (p = r(p), u = r(u));
                var h;
                return n === "keepif" ? (h = p["_op" + a](u, (y) => (g) => s(y, g)), h = h.removeUndefineds()) : h = p["_op" + a](u, (y) => (g) => Pn(y, g, s)), h;
              };
            return i.squeezein = i.squeeze, i;
          }
        });
        for (const o of e)
          f.prototype[o.toLowerCase()] = function(...i) {
            return this.set[o.toLowerCase()](i);
          };
      }
      f.prototype.struct = function(...n) {
        return this.keepif.out(...n);
      }, f.prototype.structAll = function(...n) {
        return this.keep.out(...n);
      }, f.prototype.mask = function(...n) {
        return this.keepif.in(...n);
      }, f.prototype.maskAll = function(...n) {
        return this.keep.in(...n);
      }, f.prototype.reset = function(...n) {
        return this.keepif.reset(...n);
      }, f.prototype.resetAll = function(...n) {
        return this.keep.reset(...n);
      }, f.prototype.restart = function(...n) {
        return this.keepif.restart(...n);
      }, f.prototype.restartAll = function(...n) {
        return this.keep.restart(...n);
      };
    })();
    gh = z;
    bh = z;
    _h = $t;
    pt = (t) => new f(() => [], t);
    q = pt(1);
    R = pt(0);
    Sh = w((t, e) => d(e).mask(t));
    Ah = w((t, e) => d(e).struct(t));
    Th = w((t, e) => d(e).superimpose(...t));
    Ch = w((t, e) => d(e).withValue(t));
    xh = w((t, e) => d(e).bind(t));
    Bh = w((t, e) => d(e).innerBind(t));
    Oh = w((t, e) => d(e).outerBind(t));
    zh = w((t, e) => d(e).squeezeBind(t));
    Mh = w((t, e) => d(e).stepBind(t));
    Ph = w((t, e) => d(e).polyBind(t));
    Eh = w((t, e) => d(e).set(t));
    jh = w((t, e) => d(e).keep(t));
    Jh = w((t, e) => d(e).keepif(t));
    $h = w((t, e) => d(e).add(t));
    Nh = w((t, e) => d(e).sub(t));
    Lh = w((t, e) => d(e).mul(t));
    Rh = w((t, e) => d(e).div(t));
    Wh = w((t, e) => d(e).mod(t));
    Fh = w((t, e) => d(e).pow(t));
    Ih = w((t, e) => d(e).band(t));
    Vh = w((t, e) => d(e).bor(t));
    Hh = w((t, e) => d(e).bxor(t));
    Dh = w((t, e) => d(e).blshift(t));
    Gh = w((t, e) => d(e).brshift(t));
    Qh = w((t, e) => d(e).lt(t));
    Uh = w((t, e) => d(e).gt(t));
    Xh = w((t, e) => d(e).lte(t));
    Kh = w((t, e) => d(e).gte(t));
    Yh = w((t, e) => d(e).eq(t));
    Zh = w((t, e) => d(e).eqt(t));
    td = w((t, e) => d(e).ne(t));
    ed = w((t, e) => d(e).net(t));
    nd = w((t, e) => d(e).and(t));
    sd = w((t, e) => d(e).or(t));
    rd = w((t, e) => d(e).func(t));
    od = l("round", function(t) {
      return t.asNumber().fmap((e) => Math.round(e));
    });
    cd = l("floor", function(t) {
      return t.asNumber().fmap((e) => Math.floor(e));
    });
    id = l("ceil", function(t) {
      return t.asNumber().fmap((e) => Math.ceil(e));
    });
    ud = l("toBipolar", function(t) {
      return t.fmap((e) => e * 2 - 1);
    });
    ad = l("fromBipolar", function(t) {
      return t.fmap((e) => (e + 1) / 2);
    });
    ld = l("range", function(t, e, n) {
      return n.mul(e - t).add(t);
    });
    pd = l("rangex", function(t, e, n) {
      return n._range(Math.log(t), Math.log(e)).fmap(Math.exp);
    });
    fd = l("range2", function(t, e, n) {
      return n.fromBipolar()._range(t, e);
    });
    hd = l(
      "ratio",
      (t) => t.fmap((e) => Array.isArray(e) ? e.slice(1).reduce((n, s) => n / s, e[0]) : e)
    );
    dd = l("compress", function(t, e, n) {
      return t = m(t), e = m(e), t.gt(e) || t.gt(1) || e.gt(1) || t.lt(0) || e.lt(0) ? q : n._fastGap(m(1).div(e.sub(t)))._late(t);
    });
    ({ compressSpan: md, compressspan: yd } = l(["compressSpan", "compressspan"], function(t, e) {
      return e._compress(t.begin, t.end);
    }));
    ({ fastGap: wd, fastgap: gd } = l(["fastGap", "fastgap"], function(t, e) {
      const n = function(r) {
        const o = r.begin.sam(), i = r.begin.sub(o).mul(t).min(1), a = r.end.sub(o).mul(t).min(1);
        if (!(i >= 1))
          return new B(o.add(i), o.add(a));
      }, s = function(r) {
        const o = r.part.begin, i = r.part.end, a = o.sam(), u = o.sub(a).div(t).min(1), p = i.sub(a).div(t).min(1), h = new B(a.add(u), a.add(p)), y = r.whole ? new B(
          h.begin.sub(o.sub(r.whole.begin).div(t)),
          h.end.add(r.whole.end.sub(i).div(t))
        ) : void 0;
        return new S(y, h, r.value, r.context);
      };
      return e.withQuerySpanMaybe(n).withHap(s).splitQueries();
    }));
    bd = l("focus", function(t, e, n) {
      return t = m(t), e = m(e), n._early(t.sam())._fast(m(1).div(e.sub(t)))._late(t);
    });
    ({ focusSpan: _d, focusspan: vd } = l(["focusSpan", "focusspan"], function(t, e) {
      return e._focus(t.begin, t.end);
    }));
    kd = l("ply", function(t, e) {
      const n = e.fmap((s) => C(s)._fast(t)).squeezeJoin();
      return J && (n._steps = m(t).mulmaybe(e._steps)), n;
    });
    ({ fast: qd, density: Sd } = l(
      ["fast", "density"],
      function(t, e) {
        return t === 0 ? q : (t = m(t), e.withQueryTime((s) => s.mul(t)).withHapTime((s) => s.div(t)).setSteps(e._steps));
      },
      true,
      true
    ));
    Ad = l("hurry", function(t, e) {
      return e._fast(t).mul(C({ speed: t }));
    });
    ({ slow: Td, sparsity: Cd } = l(["slow", "sparsity"], function(t, e) {
      return t === 0 ? q : e._fast(m(1).div(t));
    }));
    xd = l("inside", function(t, e, n) {
      return e(n._slow(t))._fast(t);
    });
    Bd = l("outside", function(t, e, n) {
      return e(n._fast(t))._slow(t);
    });
    Od = l("lastOf", function(t, e, n) {
      const s = Array(t - 1).fill(n);
      return s.push(e(n)), fe(...s);
    });
    ({ firstOf: zd, every: Md } = l(["firstOf", "every"], function(t, e, n) {
      const s = Array(t - 1).fill(n);
      return s.unshift(e(n)), fe(...s);
    }));
    Pd = l("apply", function(t, e) {
      return t(e);
    });
    Ed = l("cpm", function(t, e) {
      return e._fast(t / 60 / 1);
    });
    jd = l(
      "early",
      function(t, e) {
        return t = m(t), e.withQueryTime((n) => n.add(t)).withHapTime((n) => n.sub(t));
      },
      true,
      true
    );
    Ln = l(
      "late",
      function(t, e) {
        return t = m(t), e._early(m(0).sub(t));
      },
      true,
      true
    );
    Jd = l("zoom", function(t, e, n) {
      if (e = m(e), t = m(t), t.gte(e))
        return R;
      const s = e.sub(t), r = J ? n._steps?.mulmaybe(s) : void 0;
      return n.withQuerySpan((o) => o.withCycle((i) => i.mul(s).add(t))).withHapSpan((o) => o.withCycle((i) => i.sub(t).div(s))).splitQueries().setSteps(r);
    });
    ({ zoomArc: $d, zoomarc: Nd } = l(["zoomArc", "zoomarc"], function(t, e) {
      return e.zoom(t.begin, t.end);
    }));
    Ld = l(
      "bite",
      (t, e, n) => e.fmap((s) => (r) => {
        const o = m(s).div(r).mod(1), i = o.add(m(1).div(r));
        return n.zoom(o, i);
      }).appLeft(t).squeezeJoin(),
      false
    );
    Rd = l(
      "linger",
      function(t, e) {
        return t == 0 ? q : t < 0 ? e._zoom(t.add(1), 1)._slow(t) : e._zoom(0, t)._slow(t);
      },
      true,
      true
    );
    ({ segment: Wd, seg: Fd } = l(["segment", "seg"], function(t, e) {
      return e.struct(C(true)._fast(t)).setSteps(t);
    }));
    Id = l("swingBy", (t, e, n) => n.inside(e, Ln(Nn(0, t / 2))));
    Vd = l("swing", (t, e) => e.swingBy(1 / 3, t));
    ({ invert: Hd, inv: Dd } = l(
      ["invert", "inv"],
      function(t) {
        return t.fmap((e) => !e);
      },
      true,
      true
    ));
    Gd = l("when", function(t, e, n) {
      return t ? e(n) : n;
    });
    Qd = l("off", function(t, e, n) {
      return z(n, e(n.late(t)));
    });
    Ud = l("brak", function(t) {
      return t.when(Z(false, true), (e) => N(e, q)._late(0.25));
    });
    Rn = l(
      "rev",
      function(t) {
        const e = function(n) {
          const s = n.span, r = s.begin.sam(), o = s.begin.nextSam(), i = function(u) {
            const p = u.withTime((y) => r.add(o.sub(y))), h = p.begin;
            return p.begin = p.end, p.end = h, p;
          };
          return t.query(n.setSpan(i(s))).map((u) => u.withSpan(i));
        };
        return new f(e).splitQueries();
      },
      false,
      true
    );
    Xd = l("revv", function(t) {
      const e = (n) => new B(m(0).sub(n.end), m(0).sub(n.begin));
      return t.withQuerySpan(e).withHapSpan(e);
    });
    Kd = l("pressBy", function(t, e) {
      return e.fmap((n) => C(n).compress(t, 1)).squeezeJoin();
    });
    Yd = l("press", function(t) {
      return t._pressBy(0.5);
    });
    f.prototype.hush = function() {
      return q;
    };
    Zd = l(
      "palindrome",
      function(t) {
        return t.lastOf(2, Rn);
      },
      true,
      true
    );
    ({ juxBy: tm, juxby: em } = l(["juxBy", "juxby"], function(t, e, n) {
      t /= 2;
      const s = function(i, a, u) {
        return a in i ? i[a] : u;
      }, r = n.withValue((i) => Object.assign({}, i, { pan: s(i, "pan", 0.5) - t })), o = e(n.withValue((i) => Object.assign({}, i, { pan: s(i, "pan", 0.5) + t })));
      return z(r, o).setSteps(J ? Y(r._steps, o._steps) : void 0);
    }));
    nm = l("jux", function(t, e) {
      return e._juxBy(1, t, e);
    });
    ({ echoWith: sm, echowith: rm, stutWith: om, stutwith: cm } = l(
      ["echoWith", "echowith", "stutWith", "stutwith"],
      function(t, e, n, s) {
        return z(..._t(0, t - 1).map((r) => n(s.late(m(e).mul(r)), r)));
      }
    ));
    im = l("echo", function(t, e, n, s) {
      return s._echoWith(t, e, (r, o) => r.gain(Math.pow(n, o)));
    });
    um = l("stut", function(t, e, n, s) {
      return s._echoWith(t, n, (r, o) => r.gain(Math.pow(e, o)));
    });
    Wn = l("applyN", function(t, e, n) {
      let s = n;
      for (let r = 0; r < t; r++)
        s = e(s);
      return s;
    });
    am = l(["plyWith", "plywith"], function(t, e, n) {
      const s = n.fmap((r) => mt(..._t(0, t - 1).map((o) => Wn(o, e, r)))._fast(t)).squeezeJoin();
      return J && (s._steps = m(t).mulmaybe(n._steps)), s;
    });
    lm = l(["plyForEach", "plyforeach"], function(t, e, n) {
      const s = n.fmap((r) => mt(mt(C(r), ..._t(1, t - 1).map((o) => e(C(r), o))))._fast(t)).squeezeJoin();
      return J && (s._steps = m(t).mulmaybe(n._steps)), s;
    });
    jt = function(t, e, n = false) {
      return t = m(t), Z(
        ..._t(0, t.sub(1)).map(
          (s) => n ? e.late(m(s).div(t)) : e.early(m(s).div(t))
        )
      );
    };
    pm = l(
      "iter",
      function(t, e) {
        return jt(t, e, false);
      },
      true,
      true
    );
    ({ iterBack: fm, iterback: hm } = l(
      ["iterBack", "iterback"],
      function(t, e) {
        return jt(t, e, true);
      },
      true,
      true
    ));
    ({ repeatCycles: dm } = l(
      "repeatCycles",
      function(t, e) {
        return new f(function(n) {
          const s = n.span.begin.sam(), r = s.div(t).sam(), o = s.sub(r);
          return n = n.withSpan((i) => i.withTime((a) => a.sub(o))), e.query(n).map((i) => i.withSpan((a) => a.withTime((u) => u.add(o))));
        }).splitQueries();
      },
      true,
      true
    ));
    Jt = function(t, e, n, s = false, r = false) {
      const o = Array(t - 1).fill(false);
      o.unshift(true);
      const i = jt(t, Q(...o), !s);
      return r || (n = n.repeatCycles(t)), n.when(i, e);
    };
    ({ chunk: mm, slowchunk: ym, slowChunk: wm } = l(
      ["chunk", "slowchunk", "slowChunk"],
      function(t, e, n) {
        return Jt(t, e, n, false, false);
      },
      true,
      true
    ));
    ({ chunkBack: gm, chunkback: bm } = l(
      ["chunkBack", "chunkback"],
      function(t, e, n) {
        return Jt(t, e, n, true);
      },
      true,
      true
    ));
    ({ fastchunk: _m, fastChunk: vm } = l(
      ["fastchunk", "fastChunk"],
      function(t, e, n) {
        return Jt(t, e, n, false, true);
      },
      true,
      true
    ));
    ({ chunkinto: km, chunkInto: qm } = l(["chunkinto", "chunkInto"], function(t, e, n) {
      return n.into(N(true, ...Array(t - 1).fill(false))._iterback(t), e);
    }));
    ({ chunkbackinto: Sm, chunkBackInto: Am } = l(["chunkbackinto", "chunkBackInto"], function(t, e, n) {
      return n.into(
        N(true, ...Array(t - 1).fill(false))._iter(t)._early(1),
        e
      );
    }));
    Tm = l(
      "bypass",
      function(t, e) {
        return t = !!parseInt(t), t ? q : e;
      },
      true,
      true
    );
    ({ ribbon: Cm, rib: xm } = l(
      ["ribbon", "rib"],
      (t, e, n) => n.early(t).restart(C(1).slow(e))
    ));
    Bm = l("hsla", (t, e, n, s, r) => r.color(`hsla(${t}turn,${e * 100}%,${n * 100}%,${s})`));
    Om = l("hsl", (t, e, n, s) => s.color(`hsl(${t}turn,${e * 100}%,${n * 100}%)`));
    f.prototype.tag = function(t) {
      return this.withContext((e) => ({ ...e, tags: (e.tags || []).concat([t]) }));
    };
    zm = l("filter", (t, e) => e.withHaps((n) => n.filter(t)));
    Mm = l("filterWhen", (t, e) => e.filter((n) => t(n.whole.begin)));
    Pm = l(
      "within",
      (t, e, n, s) => z(
        n(s.filterWhen((r) => r.cyclePos() >= t && r.cyclePos() <= e)),
        s.filterWhen((r) => r.cyclePos() < t || r.cyclePos() > e)
      )
    );
    f.prototype.stepJoin = function() {
      const t = this, e = $(...Yt(Zt(t.queryArc(0, 1))))._steps, n = function(s) {
        const o = t.early(s.span.begin.sam()).query(s.setSpan(new B(m(0), m(1))));
        return $(...Yt(Zt(o))).query(s);
      };
      return new f(n, e);
    };
    f.prototype.stepBind = function(t) {
      return this.fmap(t).stepJoin();
    };
    Vn = l("pace", function(t, e) {
      return e._steps === void 0 ? e : e._steps.eq(m(0)) ? R : e._fast(m(t).div(e._steps)).setSteps(t);
    });
    Gn = et("take", function(t, e) {
      if (!e.hasSteps || e._steps.lte(0) || (t = m(t), t.eq(0)))
        return R;
      const n = t < 0;
      n && (t = t.abs());
      const s = t.div(e._steps);
      return s.lte(0) ? R : s.gte(1) ? e : n ? e.zoom(m(1).sub(s), 1) : e.zoom(0, s);
    });
    Qn = et("drop", function(t, e) {
      return e.hasSteps ? (t = m(t), t.lt(0) ? e.take(e._steps.add(t)) : e.take(m(0).sub(e._steps.sub(t)))) : R;
    });
    Un = et("extend", function(t, e) {
      return e.fast(t).expand(t);
    });
    Em = et("replicate", function(t, e) {
      return e.repeatCycles(t).fast(t).expand(t);
    });
    Xn = et("expand", function(t, e) {
      return e.withSteps((n) => n.mul(m(t)));
    });
    Kn = et("contract", function(t, e) {
      return e.withSteps((n) => n.div(m(t)));
    });
    f.prototype.shrinklist = function(t) {
      const e = this;
      if (!e.hasSteps)
        return [e];
      let [n, s] = Array.isArray(t) ? t : [t, e._steps];
      if (n = m(n), s === 0 || n === 0)
        return [e];
      const r = n > 0, o = [];
      if (r) {
        const i = m(1).div(e._steps).mul(n);
        for (let a = 0; a < s; ++a) {
          const u = i.mul(a);
          if (u.gt(1))
            break;
          o.push([u, 1]);
        }
      } else {
        n = m(0).sub(n);
        const i = m(1).div(e._steps).mul(n);
        for (let a = 0; a < s; ++a) {
          const u = m(1).sub(i.mul(a));
          if (u.lt(0))
            break;
          o.push([m(0), u]);
        }
      }
      return o.map((i) => e.zoom(...i));
    };
    Yn = (t, e) => e.shrinklist(t);
    Zn = l(
      "shrink",
      function(t, e) {
        if (!e.hasSteps)
          return R;
        const n = e.shrinklist(t), s = $(...n);
        return s._steps = n.reduce((r, o) => r.add(o._steps), m(0)), s;
      },
      true,
      false,
      (t) => t.stepJoin()
    );
    jm = l(
      "grow",
      function(t, e) {
        if (!e.hasSteps)
          return R;
        const n = e.shrinklist(m(0).sub(t));
        n.reverse();
        const s = $(...n);
        return s._steps = n.reduce((r, o) => r.add(o._steps), m(0)), s;
      },
      true,
      false,
      (t) => t.stepJoin()
    );
    ts = function(t, ...e) {
      return t.tour(...e);
    };
    f.prototype.tour = function(...t) {
      return $(
        ...[].concat(
          ...t.map((e, n) => [...t.slice(0, t.length - n), this, ...t.slice(t.length - n)]),
          this,
          ...t
        )
      );
    };
    es = function(...t) {
      t = t.filter((s) => s.hasSteps);
      const e = Z(...t.map((s) => s._slow(s._steps))), n = Y(...t.map((s) => s._steps));
      return e._fast(n).setSteps(n);
    };
    Jm = $;
    ns = $;
    $m = $;
    Nm = Dn;
    Lm = $t;
    f.prototype.s_polymeter = f.prototype.polymeter;
    Rm = Zn;
    f.prototype.s_taper = f.prototype.shrink;
    Wm = Yn;
    f.prototype.s_taperlist = f.prototype.shrinklist;
    Fm = Gn;
    f.prototype.s_add = f.prototype.take;
    Im = Qn;
    f.prototype.s_sub = f.prototype.drop;
    Vm = Xn;
    f.prototype.s_expand = f.prototype.expand;
    Hm = Un;
    f.prototype.s_extend = f.prototype.extend;
    Dm = Kn;
    f.prototype.s_contract = f.prototype.contract;
    Gm = ts;
    f.prototype.s_tour = f.prototype.tour;
    Qm = es;
    f.prototype.s_zip = f.prototype.zip;
    Um = Vn;
    f.prototype.steps = f.prototype.pace;
    Xm = l("chop", function(t, e) {
      const s = Array.from({ length: t }, (i, a) => a).map((i) => ({ begin: i / t, end: (i + 1) / t })), r = function(i, a) {
        if ("begin" in i && "end" in i && i.begin !== void 0 && i.end !== void 0) {
          const u = i.end - i.begin;
          a = { begin: i.begin + a.begin * u, end: i.begin + a.end * u };
        }
        return Object.assign({}, i, a);
      }, o = function(i) {
        return Q(s.map((a) => r(i, a)));
      };
      return e.squeezeBind(o).setSteps(J ? m(t).mulmaybe(e._steps) : void 0);
    });
    Km = l("striate", function(t, e) {
      const s = Array.from({ length: t }, (o, i) => i).map((o) => ({ begin: o / t, end: (o + 1) / t })), r = Z(...s);
      return e.set(r)._fast(t).setSteps(J ? m(t).mulmaybe(e._steps) : void 0);
    });
    he = function(t, e, n = 0.5) {
      return e.speed(1 / t * n).unit("c").slow(t);
    };
    ss = l(
      "slice",
      function(t, e, n) {
        return t.innerBind(
          (s) => e.outerBind(
            (r) => n.outerBind((o) => {
              o = o instanceof Object ? o : { s: o };
              const i = Array.isArray(s) ? s[r] : r / s, a = Array.isArray(s) ? s[r + 1] : (r + 1) / s;
              return C({ begin: i, end: a, _slices: s, ...o });
            })
          )
        ).setSteps(e._steps);
      },
      false
      // turns off auto-patternification
    );
    f.prototype.onTriggerTime = function(t) {
      return this.onTrigger((e, n, s, r) => {
        const o = r - n;
        window.setTimeout(() => {
          t(e);
        }, o * 1e3);
      }, false);
    };
    Ym = l(
      "splice",
      function(t, e, n) {
        const s = ss(t, e, n);
        return new f((r) => {
          const o = r.controls._cps || 1;
          return s.query(r).map(
            (a) => a.withValue((u) => ({
              speed: o / u._slices / a.whole.duration * (u.speed || 1),
              unit: "c",
              ...u
            }))
          );
        }).setSteps(e._steps);
      },
      false
      // turns off auto-patternification
    );
    ({ loopAt: Zm, loopat: ty } = l(["loopAt", "loopat"], function(t, e) {
      const n = e._steps ? e._steps.div(t) : void 0;
      return new f((s) => he(t, e, s.controls._cps).query(s), n);
    }));
    ey = l(
      "fit",
      (t) => t.withHaps(
        (e, n) => e.map(
          (s) => s.withValue((r) => {
            const o = ("end" in r ? r.end : 1) - ("begin" in r ? r.begin : 0);
            return {
              ...r,
              speed: (n.controls._cps || 1) / s.whole.duration * o,
              unit: "c"
            };
          })
        )
      )
    );
    ({ loopAtCps: ny, loopatcps: sy } = l(["loopAtCps", "loopatcps"], function(t, e, n) {
      return he(t, n, e);
    }));
    ry = (t) => C(1).withValue(() => d(t())).innerJoin();
    te = (t) => t < 0.5 ? 1 : 1 - (t - 0.5) / 0.5;
    rs = (t, e, n) => {
      e = d(e), t = d(t), n = d(n);
      let s = e.fmap((o) => ({ gain: te(o) })), r = e.fmap((o) => ({ gain: te(1 - o) }));
      return z(t.mul(s), n.mul(r));
    };
    f.prototype.xfade = function(t, e) {
      return rs(this, t, e);
    };
    os = (t) => (e, n, s) => {
      e = m(e).mod(n), n = m(n);
      const r = e.div(n), o = e.add(1).div(n);
      return t(s.fmap((i) => C(i)._compress(r, o)));
    };
    ({ beat: oy } = l(
      ["beat"],
      os((t) => t.innerJoin())
    ));
    de = (t, e, n) => {
      n = m(n);
      const s = m(1).div(t.length), r = (a) => {
        const u = [];
        for (const [p, h] of a.entries())
          h && u.push([m(p).div(a.length), h]);
        return u;
      }, o = Pt(
        ([a, u], [p, h]) => {
          const y = n.mul(p - a).add(a), g = y.add(s);
          return new B(y, g);
        },
        r(t),
        r(e)
      );
      function i(a) {
        const u = a.span.begin.sam(), p = a.span.cycleArc(), h = [];
        for (const y of o) {
          const g = y.intersection(p);
          g !== void 0 && h.push(
            new S(
              y.withTime((v) => v.add(u)),
              g.withTime((v) => v.add(u)),
              true
            )
          );
        }
        return h;
      }
      return new f(i).splitQueries();
    };
    cy = (t, e, n) => (t = d(t), e = d(e), n = d(n), t.innerBind((s) => e.innerBind((r) => n.innerBind((o) => de(s, r, o)))));
    U = function(t) {
      const e = function(n, s) {
        const r = d(n).fmap((o) => Array.isArray(o) ? [...o, t] : [o, 1, t]);
        return s ? s.distort(r) : C({}).distort(r);
      };
      return f.prototype[t] = function(n) {
        return e(n, this);
      }, e;
    };
    iy = U("soft");
    uy = U("hard");
    ay = U("cubic");
    ly = U("diode");
    py = U("asym");
    fy = U("fold");
    hy = U("sinefold");
    dy = U("chebyshev");
    me = (t) => {
      let n = C(w((...s) => s, null, t.length));
      for (const s of t) n = n.appBoth(d(s));
      return n;
    };
    vt = (t) => Array.isArray(t) ? me(t) : d(t);
    f.prototype.partials = function(t) {
      return this.withValue((e) => (n) => ({ ...e, partials: n })).appLeft(vt(t));
    };
    my = (t) => vt(t).as("partials");
    f.prototype.phases = function(t) {
      return this.withValue((e) => (n) => ({ ...e, phases: n })).appLeft(vt(t));
    };
    yy = (t) => vt(t).as("phases");
    f.prototype.FX = function(...t) {
      return t = t.map(d), this.withValue((e) => (n) => {
        const s = e.FX ?? [];
        return { ...e, FX: s.concat(n) };
      }).appLeft(me(t));
    };
    cs = (t) => {
      let n = C(w((...s) => s, null, t.length));
      for (const s of t) n = n.appLeft(s);
      return n;
    };
    f.prototype.worklet = function(t, ...e) {
      return e = e.map(d), this.outerBind((n) => cs(e).withValue((s) => {
        const r = n.workletInputs ?? [];
        return { ...n, workletSrc: t, workletInputs: r.concat(s) };
      }));
    };
    wy = (...t) => C({}).worklet(...t);
    at = /* @__PURE__ */ new Map();
    ({ s: us, sound: as } = c(["s", "n", "gain"], "sound"));
    ({ wt: ls, wavetablePosition: ps } = c("wt", "wavetablePosition"));
    ({ wtenv: fs } = c("wtenv"));
    ({ wtattack: hs, wtatt: ds } = c("wtattack", "wtatt"));
    ({ wtdecay: ms, wtdec: ys } = c("wtdecay", "wtdec"));
    ({ wtsustain: ws, wtsus: gs } = c("wtsustain", "wtsus"));
    ({ wtrelease: bs, wtrel: _s } = c("wtrelease", "wtrel"));
    ({ wtrate: vs } = c("wtrate"));
    ({ wtsync: ks } = c("wtsync"));
    ({ wtdepth: qs } = c("wtdepth"));
    ({ wtshape: Ss } = c("wtshape"));
    ({ wtdc: As } = c("wtdc"));
    ({ wtskew: Ts } = c("wtskew"));
    ({ warp: Cs, wavetableWarp: xs } = c("warp", "wavetableWarp"));
    ({ warpattack: Bs, warpatt: Os } = c("warpattack", "warpatt"));
    ({ warpdecay: zs, warpdec: Ms } = c("warpdecay", "warpdec"));
    ({ warpsustain: Ps, warpsus: Es } = c("warpsustain", "warpsus"));
    ({ warprelease: js, warprel: Js } = c("warprelease", "warprel"));
    ({ warprate: $s } = c("warprate"));
    ({ warpdepth: Ns } = c("warpdepth"));
    ({ warpshape: Ls } = c("warpshape"));
    ({ warpdc: Rs } = c("warpdc"));
    ({ warpskew: Ws } = c("warpskew"));
    ({ warpmode: Fs, wavetableWarpMode: Is } = c("warpmode", "wavetableWarpMode"));
    ({ wtphaserand: Vs, wavetablePhaseRand: Hs } = c("wtphaserand", "wavetablePhaseRand"));
    ({ warpenv: Ds } = c("warpenv"));
    ({ warpsync: Gs } = c("warpsync"));
    ({ source: Qs, src: Us } = c("source", "src"));
    ({ n: Xs } = c("n"));
    ({ note: Ks } = c(["note", "n"]));
    ({ accelerate: Ys } = c("accelerate"));
    ({ velocity: Zs, vel: tr } = c("velocity", "vel"));
    ({ gain: er } = c("gain"));
    ({ postgain: nr } = c("postgain"));
    ({ amp: sr } = c("amp"));
    ({ attack: rr, att: or } = c("attack", "att"));
    ({ fmh: cr, fmh1: ir, fmh2: ur, fmh3: ar, fmh4: lr, fmh5: pr, fmh6: fr, fmh7: hr, fmh8: dr } = V(["fmh", "fmi"], 8, "fmh"));
    ({ fmi: mr, fmi1: yr, fmi2: wr, fmi3: gr, fmi4: br, fmi5: _r, fmi6: vr, fmi7: kr, fmi8: qr, fm: Sr, fm1: Ar, fm2: Tr, fm3: Cr, fm4: xr, fm5: Br, fm6: Or, fm7: zr, fm8: Mr } = V(["fmi", "fmh"], 8, "fm"));
    ({ fmenv: Pr, fmenv1: Er, fmenv2: jr, fmenv3: Jr, fmenv4: $r, fmenv5: Nr, fmenv6: Lr, fmenv7: Rr, fmenv8: Wr } = V(
      "fmenv",
      8
    ));
    ({
      fmattack: Fr,
      fmattack1: Ir,
      fmattack2: Vr,
      fmattack3: Hr,
      fmattack4: Dr,
      fmattack5: Gr,
      fmattack6: Qr,
      fmattack7: Ur,
      fmattack8: Xr,
      fmatt: Kr,
      fmatt1: Yr,
      fmatt2: Zr,
      fmatt3: to,
      fmatt4: eo,
      fmatt5: no,
      fmatt6: so,
      fmatt7: ro,
      fmatt8: oo
    } = V("fmattack", 8, "fmatt"));
    ({ fmwave: co, fmwave1: io, fmwave2: uo, fmwave3: ao, fmwave4: lo, fmwave5: po, fmwave6: fo, fmwave7: ho, fmwave8: mo } = V(
      "fmwave",
      8
    ));
    ({
      fmdecay: yo,
      fmdecay1: wo,
      fmdecay2: go,
      fmdecay3: bo,
      fmdecay4: _o,
      fmdecay5: vo,
      fmdecay6: ko,
      fmdecay7: qo,
      fmdecay8: So,
      fmdec: Ao,
      fmdec1: To,
      fmdec2: Co,
      fmdec3: xo,
      fmdec4: Bo,
      fmdec5: Oo,
      fmdec6: zo,
      fmdec7: Mo,
      fmdec8: Po
    } = V("fmdecay", 8, "fmdec"));
    ({
      fmsustain: Eo,
      fmsustain1: jo,
      fmsustain2: Jo,
      fmsustain3: $o,
      fmsustain4: No,
      fmsustain5: Lo,
      fmsustain6: Ro,
      fmsustain7: Wo,
      fmsustain8: Fo,
      fmsus: Io,
      fmsus1: Vo,
      fmsus2: Ho,
      fmsus3: Do,
      fmsus4: Go,
      fmsus5: Qo,
      fmsus6: Uo,
      fmsus7: Xo,
      fmsus8: Ko
    } = V("fmsustain", 8, "fmsus"));
    ({
      fmrelease: Yo,
      fmrelease1: Zo,
      fmrelease2: tc,
      fmrelease3: ec,
      fmrelease4: nc,
      fmrelease5: sc,
      fmrelease6: rc,
      fmrelease7: oc,
      fmrelease8: cc,
      fmrel: ic,
      fmrel1: uc,
      fmrel2: ac,
      fmrel3: lc,
      fmrel4: pc,
      fmrel5: fc,
      fmrel6: hc,
      fmrel7: dc,
      fmrel8: mc
    } = V("fmrelease", 8, "fmrel"));
    for (let t = 0; t <= 8; t++)
      for (let e = 0; e <= 8; e++)
        c(`fmi${t}${e}`, `fm${t}${e}`);
    ({ bank: yc } = c("bank"));
    ({ chorus: wc } = c("chorus"));
    ({ analyze: gc } = c("analyze"));
    ({ fft: bc } = c("fft"));
    ({ decay: _c, dec: vc } = c("decay", "dec"));
    ({ sustain: kc, sus: qc } = c("sustain", "sus"));
    ({ release: Sc, rel: Ac } = c("release", "rel"));
    ({ hold: Tc } = c("hold"));
    ({ bandf: Cc, bpf: xc, bp: Bc } = c(["bandf", "bandq", "bpenv"], "bpf", "bp"));
    ({ bandq: Oc, bpq: zc } = c("bandq", "bpq"));
    ({ begin: Mc } = c("begin"));
    ({ end: Pc } = c("end"));
    ({ loop: Ec } = c("loop"));
    ({ loopBegin: jc, loopb: Jc } = c("loopBegin", "loopb"));
    ({ loopEnd: $c, loope: Nc } = c("loopEnd", "loope"));
    ({ crush: Lc } = c("crush"));
    ({ coarse: Rc } = c("coarse"));
    ({ tremolo: Wc, trem: Fc } = c(["tremolo", "tremolodepth", "tremoloskew", "tremolophase"], "trem"));
    ({ tremolosync: Ic } = c(
      ["tremolosync", "tremolodepth", "tremoloskew", "tremolophase"],
      "tremsync"
    ));
    ({ tremolodepth: Vc } = c("tremolodepth", "tremdepth"));
    ({ tremoloskew: Hc } = c("tremoloskew", "tremskew"));
    ({ tremolophase: Dc } = c("tremolophase", "tremphase"));
    ({ tremoloshape: Gc } = c("tremoloshape", "tremshape"));
    ({ drive: Qc } = c("drive"));
    ({ duck: Uc } = c("duckorbit", "duck"));
    ({ duckdepth: Xc } = c("duckdepth"));
    ({ duckonset: Kc } = c("duckonset", "duckons"));
    ({ duckattack: Yc } = c("duckattack", "duckatt"));
    ({ byteBeatExpression: Zc, bbexpr: ti } = c("byteBeatExpression", "bbexpr"));
    ({ byteBeatStartTime: ei, bbst: ni } = c("byteBeatStartTime", "bbst"));
    ({ channels: si, ch: ri } = c("channels", "ch"));
    ({ pw: oi } = c(["pw", "pwrate", "pwsweep"]));
    ({ pwrate: ci } = c("pwrate"));
    ({ pwsweep: ii } = c("pwsweep"));
    ({ phaserrate: ui, ph: ai, phaser: li } = c(
      ["phaserrate", "phaserdepth", "phasercenter", "phasersweep"],
      "ph",
      "phaser"
    ));
    ({ phasersweep: pi, phs: fi } = c("phasersweep", "phs"));
    ({ phasercenter: hi, phc: di } = c("phasercenter", "phc"));
    ({ phaserdepth: mi, phd: yi, phasdp: wi } = c("phaserdepth", "phd", "phasdp"));
    ({ channel: gi } = c("channel"));
    ({ cut: bi } = c("cut"));
    ({ cutoff: _i, ctf: vi, lpf: ki, lp: qi } = c(["cutoff", "resonance", "lpenv"], "ctf", "lpf", "lp"));
    ({ lpenv: Si, lpe: Ai } = c("lpenv", "lpe"));
    ({ hpenv: Ti, hpe: Ci } = c("hpenv", "hpe"));
    ({ bpenv: xi, bpe: Bi } = c("bpenv", "bpe"));
    ({ lpattack: Oi, lpa: zi } = c("lpattack", "lpa"));
    ({ hpattack: Mi, hpa: Pi } = c("hpattack", "hpa"));
    ({ bpattack: Ei, bpa: ji } = c("bpattack", "bpa"));
    ({ lpdecay: Ji, lpd: $i } = c("lpdecay", "lpd"));
    ({ hpdecay: Ni, hpd: Li } = c("hpdecay", "hpd"));
    ({ bpdecay: Ri, bpd: Wi } = c("bpdecay", "bpd"));
    ({ lpsustain: Fi, lps: Ii } = c("lpsustain", "lps"));
    ({ hpsustain: Vi, hps: Hi } = c("hpsustain", "hps"));
    ({ bpsustain: Di, bps: Gi } = c("bpsustain", "bps"));
    ({ lprelease: Qi, lpr: Ui } = c("lprelease", "lpr"));
    ({ hprelease: Xi, hpr: Ki } = c("hprelease", "hpr"));
    ({ bprelease: Yi, bpr: Zi } = c("bprelease", "bpr"));
    ({ ftype: tu } = c("ftype"));
    ({ fanchor: eu } = c("fanchor"));
    ({ lprate: nu } = c("lprate"));
    ({ lpsync: su } = c("lpsync"));
    ({ lpdepth: ru } = c("lpdepth"));
    ({ lpdepthfrequency: ou, lpdepthfreq: cu } = c("lpdepthfrequency", "lpdepthfreq"));
    ({ lpshape: iu } = c("lpshape"));
    ({ lpdc: uu } = c("lpdc"));
    ({ lpskew: au } = c("lpskew"));
    ({ bprate: lu } = c("bprate"));
    ({ bpsync: pu } = c("bpsync"));
    ({ bpdepth: fu } = c("bpdepth"));
    ({ bpdepthfrequency: hu, bpdepthfreq: du } = c("bpdepthfrequency", "bpdepthfreq"));
    ({ bpshape: mu } = c("bpshape"));
    ({ bpdc: yu } = c("bpdc"));
    ({ bpskew: wu } = c("bpskew"));
    ({ hprate: gu } = c("hprate"));
    ({ hpsync: bu } = c("hpsync"));
    ({ hpdepth: _u } = c("hpdepth"));
    ({ hpdepthfrequency: vu, hpdepthfreq: ku } = c("hpdepthfrequency", "hpdepthfreq"));
    ({ hpshape: qu } = c("hpshape"));
    ({ hpdc: Su } = c("hpdc"));
    ({ hpskew: Au } = c("hpskew"));
    ({ vib: Tu, vibrato: Cu, v: xu } = c(["vib", "vibmod"], "vibrato", "v"));
    ({ noise: Bu } = c("noise"));
    ({ vibmod: Ou, vmod: zu } = c(["vibmod", "vib"], "vmod"));
    ({ hcutoff: Mu, hpf: Pu, hp: Eu } = c(["hcutoff", "hresonance", "hpenv"], "hpf", "hp"));
    ({ hresonance: ju, hpq: Ju } = c("hresonance", "hpq"));
    ({ resonance: $u, lpq: Nu } = c("resonance", "lpq"));
    ({ djf: Lu } = c("djf"));
    ({ delay: Ru } = c(["delay", "delaytime", "delayfeedback"]));
    ({ delayfeedback: Wu, delayfb: Fu, dfb: Iu } = c("delayfeedback", "delayfb", "dfb"));
    ({ delayspeed: Vu } = c("delayspeed"));
    ({ delaytime: Hu, delayt: Du, dt: Gu } = c("delaytime", "delayt", "dt"));
    ({ delaysync: Qu } = c("delaysync"));
    ({ lock: Uu } = c("lock"));
    ({ detune: Xu, det: Ku } = c("detune", "det"));
    ({ unison: Yu } = c("unison"));
    ({ spread: Zu } = c("spread"));
    ({ dry: ta } = c("dry"));
    ({ fadeTime: ea, fadeOutTime: na } = c("fadeTime", "fadeOutTime"));
    ({ fadeInTime: sa } = c("fadeInTime"));
    ({ freq: ra } = c("freq"));
    ({ pattack: oa, patt: ca } = c("pattack", "patt"));
    ({ pdecay: ia, pdec: ua } = c("pdecay", "pdec"));
    ({ psustain: aa, psus: la } = c("psustain", "psus"));
    ({ prelease: pa, prel: fa } = c("prelease", "prel"));
    ({ penv: ha } = c("penv"));
    ({ pcurve: da } = c("pcurve"));
    ({ panchor: ma } = c("panchor"));
    ({ gate: ya, gat: wa } = c("gate", "gat"));
    ({ leslie: ga } = c("leslie"));
    ({ lrate: ba } = c("lrate"));
    ({ lsize: _a } = c("lsize"));
    ({ activeLabel: va } = c("activeLabel"));
    ({ label: ka } = c(["label", "activeLabel"]));
    ({ degree: qa } = c("degree"));
    ({ mtranspose: Sa } = c("mtranspose"));
    ({ ctranspose: Aa } = c("ctranspose"));
    ({ harmonic: Ta } = c("harmonic"));
    ({ stepsPerOctave: Ca } = c("stepsPerOctave"));
    ({ octaveR: xa } = c("octaveR"));
    ({ nudge: Ba } = c("nudge"));
    ({ octave: Oa, oct: za } = c("octave", "oct"));
    ({ orbit: Ma } = c("orbit", "o"));
    ({ bus: Pa } = c("bus"));
    ({ busgain: Ea, bgain: ja } = c("busgain", "bgain"));
    ({ overgain: Ja } = c("overgain"));
    ({ overshape: $a } = c("overshape"));
    ({ pan: Na } = c("pan"));
    ({ panspan: La } = c("panspan"));
    ({ pansplay: Ra } = c("pansplay"));
    ({ panwidth: Wa } = c("panwidth"));
    ({ panorient: Fa } = c("panorient"));
    ({ slide: Ia } = c("slide"));
    ({ semitone: Va } = c("semitone"));
    ({ voice: Ha } = c("voice"));
    ({ chord: Da } = c("chord"));
    ({ dictionary: Ga, dict: Qa } = c("dictionary", "dict"));
    ({ anchor: Ua } = c("anchor"));
    ({ offset: Xa } = c("offset"));
    ({ octaves: Ka } = c("octaves"));
    ({ mode: Ya } = c(["mode", "anchor"]));
    ({ room: Za } = c(["room", "size"]));
    ({ roomlp: tl, rlp: el } = c("roomlp", "rlp"));
    ({ roomdim: nl, rdim: sl } = c("roomdim", "rdim"));
    ({ roomfade: rl, rfade: ol } = c("roomfade", "rfade"));
    ({ ir: cl, iresponse: il } = c(["ir", "i"], "iresponse"));
    ({ irspeed: ul } = c("irspeed"));
    ({ irbegin: al } = c("irbegin"));
    ({ roomsize: ll, size: pl, sz: fl, rsize: hl } = c("roomsize", "size", "sz", "rsize"));
    ({ shape: dl } = c(["shape", "shapevol"]));
    ({ distort: ml, dist: yl } = c(["distort", "distortvol", "distorttype"], "dist"));
    ({ distortvol: wl } = c("distortvol", "distvol"));
    ({ distorttype: gl } = c("distorttype", "disttype"));
    ({ compressor: bl } = c([
      "compressor",
      "compressorRatio",
      "compressorKnee",
      "compressorAttack",
      "compressorRelease"
    ]));
    ({ compressorKnee: _l } = c("compressorKnee"));
    ({ compressorRatio: vl } = c("compressorRatio"));
    ({ compressorAttack: kl } = c("compressorAttack"));
    ({ compressorRelease: ql } = c("compressorRelease"));
    ({ speed: ye } = c("speed"));
    ({ stretch: Sl } = c("stretch"));
    ({ unit: Al } = c("unit"));
    ({ squiz: Tl } = c("squiz"));
    ({ vowel: Cl } = c("vowel"));
    ({ waveloss: xl } = c("waveloss"));
    ({ density: Bl } = c("density"));
    ({ expression: Ol } = c("expression"));
    ({ sustainpedal: zl } = c("sustainpedal"));
    ({ fshift: Ml } = c("fshift"));
    ({ fshiftnote: Pl } = c("fshiftnote"));
    ({ fshiftphase: El } = c("fshiftphase"));
    ({ triode: jl } = c("triode"));
    ({ krush: Jl } = c("krush"));
    ({ kcutoff: $l } = c("kcutoff"));
    ({ octer: Nl } = c("octer"));
    ({ octersub: Ll } = c("octersub"));
    ({ octersubsub: Rl } = c("octersubsub"));
    ({ ring: Wl } = c("ring"));
    ({ ringf: Fl } = c("ringf"));
    ({ ringdf: Il } = c("ringdf"));
    ({ freeze: Vl } = c("freeze"));
    ({ xsdelay: Hl } = c("xsdelay"));
    ({ tsdelay: Dl } = c("tsdelay"));
    ({ real: Gl } = c("real"));
    ({ imag: Ql } = c("imag"));
    ({ enhance: Ul } = c("enhance"));
    ({ comb: Xl } = c("comb"));
    ({ smear: Kl } = c("smear"));
    ({ scram: Yl } = c("scram"));
    ({ binshift: Zl } = c("binshift"));
    ({ hbrick: tp } = c("hbrick"));
    ({ lbrick: ep } = c("lbrick"));
    ({ frameRate: np } = c("frameRate"));
    ({ frames: sp } = c("frames"));
    ({ hours: rp } = c("hours"));
    ({ minutes: op } = c("minutes"));
    ({ seconds: cp } = c("seconds"));
    ({ songPtr: ip } = c("songPtr"));
    ({ uid: up } = c("uid"));
    ({ val: ap } = c("val"));
    ({ cps: lp } = c("cps"));
    ({ clip: pp, legato: fp } = c("clip", "legato"));
    ({ duration: hp, dur: dp } = c("duration", "dur"));
    ({ zrand: mp } = c("zrand"));
    ({ curve: yp } = c("curve"));
    ({ deltaSlide: wp } = c("deltaSlide"));
    ({ pitchJump: gp } = c("pitchJump"));
    ({ pitchJumpTime: bp } = c("pitchJumpTime"));
    ({ znoise: _p } = c("znoise"));
    ({ zmod: vp } = c("zmod"));
    ({ zcrush: kp } = c("zcrush"));
    ({ zdelay: qp } = c("zdelay"));
    ({ zzfx: Sp } = c("zzfx"));
    ({ color: Ap, colour: Tp } = c(["color", "colour"]));
    Cp = (...t) => t.reduce((e, n) => Object.assign(e, { [n]: Nt(n) }), {});
    xp = l("adsr", (t, e) => {
      t = Array.isArray(t) ? t : [t];
      const [n, s, r, o] = t;
      return e.set({ attack: n, decay: s, sustain: r, release: o });
    });
    Bp = l("ad", (t, e) => {
      t = Array.isArray(t) ? t : [t];
      const [n, s = n] = t;
      return e.attack(n).decay(s);
    });
    Op = l("ds", (t, e) => {
      t = Array.isArray(t) ? t : [t];
      const [n, s = 0] = t;
      return e.set({ decay: n, sustain: s });
    });
    zp = l("ar", (t, e) => {
      t = Array.isArray(t) ? t : [t];
      const [n, s = n] = t;
      return e.set({ attack: n, release: s });
    });
    ({ midichan: Mp } = c("midichan"));
    ({ midimap: Pp } = c("midimap"));
    ({ midiport: Ep } = c("midiport"));
    ({ midicmd: jp } = c("midicmd"));
    Jp = l("control", (t, e) => {
      if (!Array.isArray(t))
        throw new Error("control expects an array of [ccn, ccv]");
      const [n, s] = t;
      return e.ccn(n).ccv(s);
    });
    ({ ccn: $p } = c("ccn"));
    ({ ccv: Np } = c("ccv"));
    ({ ctlNum: Lp } = c("ctlNum"));
    ({ nrpnn: Rp } = c("nrpnn"));
    ({ nrpv: Wp } = c("nrpv"));
    ({ progNum: Fp } = c("progNum"));
    Ip = l("sysex", (t, e) => {
      if (!Array.isArray(t))
        throw new Error("sysex expects an array of [id, data]");
      const [n, s] = t;
      return e.sysexid(n).sysexdata(s);
    });
    ({ sysexid: Vp } = c("sysexid"));
    ({ sysexdata: Hp } = c("sysexdata"));
    ({ midibend: Dp } = c("midibend"));
    ({ miditouch: Gp } = c("miditouch"));
    ({ polyTouch: Qp } = c("polyTouch"));
    ({ oschost: Up } = c("oschost"));
    ({ oscport: Xp } = c("oscport"));
    yt = (t) => at.has(t) ? at.get(t) : t;
    Kp = l("as", (t, e) => (t = Array.isArray(t) ? t : [t], e.fmap((n) => {
      n = Array.isArray(n) ? n : [n];
      const s = [];
      for (let r = 0; r < t.length; ++r)
        n[r] !== void 0 && s.push([yt(t[r]), n[r]]);
      return Object.fromEntries(s);
    })));
    Yp = l(
      "scrub",
      (t, e) => t.outerBind((n) => {
        Array.isArray(n) || (n = [n]);
        const [s, r = 1] = n;
        return e.begin(s).mul(ye(r)).clip(1);
      }),
      false
    );
    Bt = /* @__PURE__ */ new Map();
    Zp = (t, e, ...n) => {
      const s = Bt.get(t) ?? /* @__PURE__ */ new Map(), r = /* @__PURE__ */ new Set([e, ...n]);
      for (const o of r)
        s.set(String(o).toLowerCase(), e);
      Bt.set(t, s);
    };
    Lt = (t, e = []) => {
      for (const [n, ...s] of e)
        Zp(t, n, ...s);
    };
    tf = (t, e) => {
      const n = Bt.get(t);
      return n ? n.get(String(e).toLowerCase()) ?? e : e;
    };
    Lt("lfo", [
      ["control", "c"],
      ["subControl", "sc"],
      ["rate", "r"],
      ["depth", "dep", "dr"],
      ["depthabs", "da"],
      ["dcoffset", "dc"],
      ["shape", "sh"],
      ["skew", "sk"],
      ["curve", "cu"],
      ["sync", "s"],
      ["fxi"]
    ]);
    Lt("env", [
      ["control", "c"],
      ["subControl", "sc"],
      ["attack", "att", "a"],
      ["decay", "dec", "d"],
      ["sustain", "sus", "s"],
      ["release", "rel", "r"],
      ["depth", "dep", "dr"],
      ["depthabs", "da"],
      ["acurve", "ac"],
      ["dcurve", "dc"],
      ["rcurve", "rc"],
      ["fxi"]
    ]);
    Lt("bmod", [
      ["bus", "b"],
      ["control", "c"],
      ["subControl", "sc"],
      ["depth", "dep", "dr"],
      ["depthabs", "da"],
      ["dc"],
      ["fxi"]
    ]);
    f.prototype.modulate = function(t, e, n) {
      e = { control: void 0, ...e };
      const s = ["lfo", "env", "bmod"];
      if (!s.includes(t))
        return E(`[core] Modulation type ${t} not found. Please use one of 'lfo', 'env', 'bmod'`), this;
      let r = this, o;
      r = r.fmap((i) => (a) => ({ v: i, id: a })).appLeft(d(n));
      for (const [i, a] of Object.entries(e)) {
        const u = tf(t, i), p = d(a);
        r = r.fmap(({ v: h, id: y }) => (g) => {
          if (o === void 0) {
            let _ = yt(Object.keys(h).at(-1));
            s.includes(_) && (_ = `${_}_${[...h[_].__ids].at(-1)}`), o = _;
          }
          h[t] ??= { __ids: /* @__PURE__ */ new Set() };
          const v = h[t];
          return y ??= v.__ids.size, v[y] ??= { control: o }, v.__ids.add(y), g === void 0 ? { v: h, id: y } : (u === "control" || u === "subControl" ? v[y][u] = yt(g) : v[y][u] = g, { v: h, id: y });
        }).appLeft(p);
      }
      return r.fmap(({ v: i }) => i);
    };
    f.prototype.lfo = function(t, e) {
      return this.modulate("lfo", t, e);
    };
    ef = (t) => C({}).lfo(t);
    f.prototype.env = function(t, e) {
      return this.modulate("env", t, e);
    };
    nf = (t) => C({}).env(t);
    f.prototype.bmod = function(t, e) {
      return this.modulate("bmod", t, e);
    };
    sf = (t) => C({}).bmod(t);
    ({ transient: rf } = c(["transient", "transsustain"]));
    ({ FXrelease: of, FXrel: cf, FXr: uf, fxr: af } = c("FXrelease", "FXrel", "FXr", "fxr"));
    gy = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
      __proto__: null,
      FXr: uf,
      FXrel: cf,
      FXrelease: of,
      accelerate: Ys,
      activeLabel: va,
      ad: Bp,
      adsr: xp,
      amp: sr,
      analyze: gc,
      anchor: Ua,
      ar: zp,
      as: Kp,
      att: or,
      attack: rr,
      bandf: Cc,
      bandq: Oc,
      bank: yc,
      bbexpr: ti,
      bbst: ni,
      begin: Mc,
      bgain: ja,
      binshift: Zl,
      bmod: sf,
      bp: Bc,
      bpa: ji,
      bpattack: Ei,
      bpd: Wi,
      bpdc: yu,
      bpdecay: Ri,
      bpdepth: fu,
      bpdepthfreq: du,
      bpdepthfrequency: hu,
      bpe: Bi,
      bpenv: xi,
      bpf: xc,
      bpq: zc,
      bpr: Zi,
      bprate: lu,
      bprelease: Yi,
      bps: Gi,
      bpshape: mu,
      bpskew: wu,
      bpsustain: Di,
      bpsync: pu,
      bus: Pa,
      busgain: Ea,
      byteBeatExpression: Zc,
      byteBeatStartTime: ei,
      ccn: $p,
      ccv: Np,
      ch: ri,
      channel: gi,
      channels: si,
      chord: Da,
      chorus: wc,
      clip: pp,
      coarse: Rc,
      color: Ap,
      colour: Tp,
      comb: Xl,
      compressor: bl,
      compressorAttack: kl,
      compressorKnee: _l,
      compressorRatio: vl,
      compressorRelease: ql,
      control: Jp,
      cps: lp,
      createParam: Nt,
      createParams: Cp,
      crush: Lc,
      ctf: vi,
      ctlNum: Lp,
      ctranspose: Aa,
      curve: yp,
      cut: bi,
      cutoff: _i,
      dec: vc,
      decay: _c,
      degree: qa,
      delay: Ru,
      delayfb: Fu,
      delayfeedback: Wu,
      delayspeed: Vu,
      delaysync: Qu,
      delayt: Du,
      delaytime: Hu,
      deltaSlide: wp,
      density: Bl,
      det: Ku,
      detune: Xu,
      dfb: Iu,
      dict: Qa,
      dictionary: Ga,
      dist: yl,
      distort: ml,
      distorttype: gl,
      distortvol: wl,
      djf: Lu,
      drive: Qc,
      dry: ta,
      ds: Op,
      dt: Gu,
      duck: Uc,
      duckattack: Yc,
      duckdepth: Xc,
      duckonset: Kc,
      dur: dp,
      duration: hp,
      end: Pc,
      enhance: Ul,
      env: nf,
      expression: Ol,
      fadeInTime: sa,
      fadeOutTime: na,
      fadeTime: ea,
      fanchor: eu,
      fft: bc,
      fm: Sr,
      fm1: Ar,
      fm2: Tr,
      fm3: Cr,
      fm4: xr,
      fm5: Br,
      fm6: Or,
      fm7: zr,
      fm8: Mr,
      fmatt: Kr,
      fmatt1: Yr,
      fmatt2: Zr,
      fmatt3: to,
      fmatt4: eo,
      fmatt5: no,
      fmatt6: so,
      fmatt7: ro,
      fmatt8: oo,
      fmattack: Fr,
      fmattack1: Ir,
      fmattack2: Vr,
      fmattack3: Hr,
      fmattack4: Dr,
      fmattack5: Gr,
      fmattack6: Qr,
      fmattack7: Ur,
      fmattack8: Xr,
      fmdec: Ao,
      fmdec1: To,
      fmdec2: Co,
      fmdec3: xo,
      fmdec4: Bo,
      fmdec5: Oo,
      fmdec6: zo,
      fmdec7: Mo,
      fmdec8: Po,
      fmdecay: yo,
      fmdecay1: wo,
      fmdecay2: go,
      fmdecay3: bo,
      fmdecay4: _o,
      fmdecay5: vo,
      fmdecay6: ko,
      fmdecay7: qo,
      fmdecay8: So,
      fmenv: Pr,
      fmenv1: Er,
      fmenv2: jr,
      fmenv3: Jr,
      fmenv4: $r,
      fmenv5: Nr,
      fmenv6: Lr,
      fmenv7: Rr,
      fmenv8: Wr,
      fmh: cr,
      fmh1: ir,
      fmh2: ur,
      fmh3: ar,
      fmh4: lr,
      fmh5: pr,
      fmh6: fr,
      fmh7: hr,
      fmh8: dr,
      fmi: mr,
      fmi1: yr,
      fmi2: wr,
      fmi3: gr,
      fmi4: br,
      fmi5: _r,
      fmi6: vr,
      fmi7: kr,
      fmi8: qr,
      fmrel: ic,
      fmrel1: uc,
      fmrel2: ac,
      fmrel3: lc,
      fmrel4: pc,
      fmrel5: fc,
      fmrel6: hc,
      fmrel7: dc,
      fmrel8: mc,
      fmrelease: Yo,
      fmrelease1: Zo,
      fmrelease2: tc,
      fmrelease3: ec,
      fmrelease4: nc,
      fmrelease5: sc,
      fmrelease6: rc,
      fmrelease7: oc,
      fmrelease8: cc,
      fmsus: Io,
      fmsus1: Vo,
      fmsus2: Ho,
      fmsus3: Do,
      fmsus4: Go,
      fmsus5: Qo,
      fmsus6: Uo,
      fmsus7: Xo,
      fmsus8: Ko,
      fmsustain: Eo,
      fmsustain1: jo,
      fmsustain2: Jo,
      fmsustain3: $o,
      fmsustain4: No,
      fmsustain5: Lo,
      fmsustain6: Ro,
      fmsustain7: Wo,
      fmsustain8: Fo,
      fmwave: co,
      fmwave1: io,
      fmwave2: uo,
      fmwave3: ao,
      fmwave4: lo,
      fmwave5: po,
      fmwave6: fo,
      fmwave7: ho,
      fmwave8: mo,
      frameRate: np,
      frames: sp,
      freeze: Vl,
      freq: ra,
      fshift: Ml,
      fshiftnote: Pl,
      fshiftphase: El,
      ftype: tu,
      fxr: af,
      gain: er,
      gat: wa,
      gate: ya,
      getControlName: yt,
      harmonic: Ta,
      hbrick: tp,
      hcutoff: Mu,
      hold: Tc,
      hours: rp,
      hp: Eu,
      hpa: Pi,
      hpattack: Mi,
      hpd: Li,
      hpdc: Su,
      hpdecay: Ni,
      hpdepth: _u,
      hpdepthfreq: ku,
      hpdepthfrequency: vu,
      hpe: Ci,
      hpenv: Ti,
      hpf: Pu,
      hpq: Ju,
      hpr: Ki,
      hprate: gu,
      hprelease: Xi,
      hps: Hi,
      hpshape: qu,
      hpskew: Au,
      hpsustain: Vi,
      hpsync: bu,
      hresonance: ju,
      imag: Ql,
      ir: cl,
      irbegin: al,
      iresponse: il,
      irspeed: ul,
      isControlName: is,
      kcutoff: $l,
      krush: Jl,
      label: ka,
      lbrick: ep,
      legato: fp,
      leslie: ga,
      lfo: ef,
      lock: Uu,
      loop: Ec,
      loopBegin: jc,
      loopEnd: $c,
      loopb: Jc,
      loope: Nc,
      lp: qi,
      lpa: zi,
      lpattack: Oi,
      lpd: $i,
      lpdc: uu,
      lpdecay: Ji,
      lpdepth: ru,
      lpdepthfreq: cu,
      lpdepthfrequency: ou,
      lpe: Ai,
      lpenv: Si,
      lpf: ki,
      lpq: Nu,
      lpr: Ui,
      lprate: nu,
      lprelease: Qi,
      lps: Ii,
      lpshape: iu,
      lpskew: au,
      lpsustain: Fi,
      lpsync: su,
      lrate: ba,
      lsize: _a,
      midibend: Dp,
      midichan: Mp,
      midicmd: jp,
      midimap: Pp,
      midiport: Ep,
      miditouch: Gp,
      minutes: op,
      mode: Ya,
      mtranspose: Sa,
      n: Xs,
      noise: Bu,
      note: Ks,
      nrpnn: Rp,
      nrpv: Wp,
      nudge: Ba,
      oct: za,
      octave: Oa,
      octaveR: xa,
      octaves: Ka,
      octer: Nl,
      octersub: Ll,
      octersubsub: Rl,
      offset: Xa,
      orbit: Ma,
      oschost: Up,
      oscport: Xp,
      overgain: Ja,
      overshape: $a,
      pan: Na,
      panchor: ma,
      panorient: Fa,
      panspan: La,
      pansplay: Ra,
      panwidth: Wa,
      patt: ca,
      pattack: oa,
      pcurve: da,
      pdec: ua,
      pdecay: ia,
      penv: ha,
      ph: ai,
      phasdp: wi,
      phaser: li,
      phasercenter: hi,
      phaserdepth: mi,
      phaserrate: ui,
      phasersweep: pi,
      phc: di,
      phd: yi,
      phs: fi,
      pitchJump: gp,
      pitchJumpTime: bp,
      polyTouch: Qp,
      postgain: nr,
      prel: fa,
      prelease: pa,
      progNum: Fp,
      psus: la,
      psustain: aa,
      pw: oi,
      pwrate: ci,
      pwsweep: ii,
      rdim: sl,
      real: Gl,
      registerControl: c,
      registerMultiControl: V,
      rel: Ac,
      release: Sc,
      resonance: $u,
      rfade: ol,
      ring: Wl,
      ringdf: Il,
      ringf: Fl,
      rlp: el,
      room: Za,
      roomdim: nl,
      roomfade: rl,
      roomlp: tl,
      roomsize: ll,
      rsize: hl,
      s: us,
      scram: Yl,
      scrub: Yp,
      seconds: cp,
      semitone: Va,
      shape: dl,
      size: pl,
      slide: Ia,
      smear: Kl,
      songPtr: ip,
      sound: as,
      source: Qs,
      speed: ye,
      spread: Zu,
      squiz: Tl,
      src: Us,
      stepsPerOctave: Ca,
      stretch: Sl,
      sus: qc,
      sustain: kc,
      sustainpedal: zl,
      sysex: Ip,
      sysexdata: Hp,
      sysexid: Vp,
      sz: fl,
      transient: rf,
      trem: Fc,
      tremolo: Wc,
      tremolodepth: Vc,
      tremolophase: Dc,
      tremoloshape: Gc,
      tremoloskew: Hc,
      tremolosync: Ic,
      triode: jl,
      tsdelay: Dl,
      uid: up,
      unison: Yu,
      unit: Al,
      v: xu,
      val: ap,
      vel: tr,
      velocity: Zs,
      vib: Tu,
      vibmod: Ou,
      vibrato: Cu,
      vmod: zu,
      voice: Ha,
      vowel: Cl,
      warp: Cs,
      warpatt: Os,
      warpattack: Bs,
      warpdc: Rs,
      warpdec: Ms,
      warpdecay: zs,
      warpdepth: Ns,
      warpenv: Ds,
      warpmode: Fs,
      warprate: $s,
      warprel: Js,
      warprelease: js,
      warpshape: Ls,
      warpskew: Ws,
      warpsus: Es,
      warpsustain: Ps,
      warpsync: Gs,
      waveloss: xl,
      wavetablePhaseRand: Hs,
      wavetablePosition: ps,
      wavetableWarp: xs,
      wavetableWarpMode: Is,
      wt: ls,
      wtatt: ds,
      wtattack: hs,
      wtdc: As,
      wtdec: ys,
      wtdecay: ms,
      wtdepth: qs,
      wtenv: fs,
      wtphaserand: Vs,
      wtrate: vs,
      wtrel: _s,
      wtrelease: bs,
      wtshape: Ss,
      wtskew: Ts,
      wtsus: gs,
      wtsustain: ws,
      wtsync: ks,
      xsdelay: Hl,
      zcrush: kp,
      zdelay: qp,
      zmod: vp,
      znoise: _p,
      zrand: mp,
      zzfx: Sp
    }, Symbol.toStringTag, { value: "Module" }));
    lf = function(t, e) {
      const [n, s] = t, [r, o] = e, [i, a] = ue(s, r);
      return [
        [s, n - s],
        [Pt((u, p) => u.concat(p), i, o), a]
      ];
    };
    pf = function(t, e) {
      const [n, s] = t, [r, o] = e, [i, a] = ue(n, o);
      return [
        [n, s - n],
        [Pt((p, h) => p.concat(h), r, i), a]
      ];
    };
    we = function(t, e) {
      const [n, s] = t;
      return Math.min(n, s) <= 1 ? [t, e] : we(...n > s ? lf(t, e) : pf(t, e));
    };
    ge = function(t, e) {
      const n = t < 0, s = Math.abs(t), r = e - s, o = Array(s).fill([1]), i = Array(r).fill([0]), a = we([s, r], [o, i]), u = G(a[1][0]).concat(G(a[1][1]));
      return n ? u.map((p) => 1 - p) : u;
    };
    kt = function(t, e, n) {
      const s = ge(t, e);
      return n ? rn(s, -n) : s;
    };
    by = l("euclid", function(t, e, n) {
      return n.struct(kt(t, e, 0));
    });
    _y = l("bjork", function(t, e) {
      Array.isArray(t) || (t = [t]);
      const [n, s = n, r = 0] = t;
      return e.struct(kt(n, s, r));
    });
    ({ euclidrot: vy, euclidRot: ky } = l(["euclidrot", "euclidRot"], function(t, e, n, s) {
      return s.struct(kt(t, e, n));
    }));
    be = function(t, e, n, s) {
      if (t < 1)
        return q;
      const o = kt(t, e, 0).join("").split("1").slice(1).map((i) => [i.length + 1, true]);
      return s.struct(ns(...o)).late(m(n).div(e));
    };
    qy = l(["euclidLegato"], function(t, e, n) {
      return be(t, e, 0, n);
    });
    Sy = l(["euclidLegatoRot"], function(t, e, n, s) {
      return be(t, e, n, s);
    });
    ({ euclidish: Ay, eish: Ty } = l(["euclidish", "eish"], function(t, e, n, s) {
      const r = de(ge(t, e), new Array(t).fill(1), n);
      return s.struct(r).setSteps(e);
    }));
    hf = class {
      constructor({
        interval: e,
        onTrigger: n,
        onToggle: s,
        onError: r,
        getTime: o,
        latency: i = 0.1,
        setInterval: a,
        clearInterval: u,
        beforeStart: p
      }) {
        this.started = false, this.beforeStart = p, this.cps = 0.5, this.num_ticks_since_cps_change = 0, this.lastTick = 0, this.lastBegin = 0, this.lastEnd = 0, this.getTime = o, this.num_cycles_at_cps_change = 0, this.seconds_at_cps_change, this.onToggle = s, this.latency = i, this.clock = ff(
          o,
          // called slightly before each cycle
          (h, y, g, v) => {
            this.num_ticks_since_cps_change === 0 && (this.num_cycles_at_cps_change = this.lastEnd, this.seconds_at_cps_change = h), this.num_ticks_since_cps_change++;
            const O = this.num_ticks_since_cps_change * y * this.cps;
            try {
              const A = this.lastEnd;
              this.lastBegin = A;
              const I = this.num_cycles_at_cps_change + O;
              if (this.lastEnd = I, this.lastTick = h, h < v) {
                console.log("skip query: too late");
                return;
              }
              this.pattern.queryArc(A, I, { _cps: this.cps, cyclist: "cyclist" }).forEach((P2) => {
                if (P2.hasOnset()) {
                  const x = (P2.whole.begin - this.num_cycles_at_cps_change) / this.cps + this.seconds_at_cps_change + i, D = P2.duration / this.cps, nt = x - h;
                  n?.(P2, nt, D, this.cps, x), P2.value.cps !== void 0 && this.cps != P2.value.cps && (this.cps = P2.value.cps, this.num_ticks_since_cps_change = 0);
                }
              });
            } catch (A) {
              zt(A), r?.(A);
            }
          },
          e,
          // duration of each cycle
          0.1,
          0.1,
          a,
          u
        );
      }
      now() {
        if (!this.started)
          return 0;
        const e = this.getTime() - this.lastTick - this.clock.duration;
        return this.lastBegin + e * this.cps;
      }
      setStarted(e) {
        this.started = e, this.onToggle?.(e);
      }
      async start() {
        if (await this.beforeStart?.(), this.num_ticks_since_cps_change = 0, this.num_cycles_at_cps_change = 0, !this.pattern)
          throw new Error("Scheduler: no pattern set! call .setPattern first.");
        E("[cyclist] start"), this.clock.start(), this.setStarted(true);
      }
      pause() {
        E("[cyclist] pause"), this.clock.pause(), this.setStarted(false);
      }
      stop() {
        E("[cyclist] stop"), this.clock.stop(), this.lastEnd = 0, this.setStarted(false);
      }
      async setPattern(e, n = false) {
        this.pattern = e, n && !this.started && await this.start();
      }
      setCps(e = 0.5) {
        this.cps !== e && (this.cps = e, this.num_ticks_since_cps_change = 0);
      }
      log(e, n, s) {
        const r = s.filter((o) => o.hasOnset());
        console.log(`${e.toFixed(4)} - ${n.toFixed(4)} ${Array(r.length).fill("I").join("")}`);
      }
    };
    ct = {};
    df = function() {
      mf();
    };
    mf = function() {
      ct = {};
    };
    Cy = l(
      "timeline",
      function(t, e) {
        t = d(t);
        const n = function(s) {
          const r = !!s.controls.cyclist, o = t.query(s), i = [];
          for (const a of o) {
            const u = a.value;
            let p;
            if (u === 0)
              p = 0;
            else if (u in ct)
              p = ct[u];
            else {
              const y = a.wholeOrPart();
              !r || s.span.begin.lt(y.midpoint()) ? p = y.begin : p = y.end;
            }
            r && (ct[u] = p, u !== 0 && delete ct[-u]);
            const h = e.late(p).query(s.setSpan(a.part)).map((y) => y.setContext(y.combineContext(a)));
            i.push(...h);
          }
          return i;
        };
        return new f(n, e._steps);
      },
      false
    );
    F = function(t, e, n = true) {
      const s = Array.isArray(t), r = Object.keys(t).length;
      return t = bn(t, d), r === 0 ? q : e.fmap((o) => {
        let i = o;
        return s && (i = n ? Math.round(i) % r : an(Math.round(i), 0, t.length - 1)), t[i];
      });
    };
    yf = function(t, e) {
      return Array.isArray(e) && ([e, t] = [t, e]), wf(t, e);
    };
    wf = l("pick", function(t, e) {
      return F(t, e, false).innerJoin();
    });
    gf = l("pickmod", function(t, e) {
      return F(t, e, true).innerJoin();
    });
    xy = l("pickF", function(t, e, n) {
      return n.apply(yf(t, e));
    });
    By = l("pickmodF", function(t, e, n) {
      return n.apply(gf(t, e));
    });
    Oy = l("pickOut", function(t, e) {
      return F(t, e, false).outerJoin();
    });
    zy = l("pickmodOut", function(t, e) {
      return F(t, e, true).outerJoin();
    });
    My = l("pickRestart", function(t, e) {
      return F(t, e, false).restartJoin();
    });
    Py = l("pickmodRestart", function(t, e) {
      return F(t, e, true).restartJoin();
    });
    Ey = l("pickReset", function(t, e) {
      return F(t, e, false).resetJoin();
    });
    jy = l("pickmodReset", function(t, e) {
      return F(t, e, true).resetJoin();
    });
    ({ inhabit: Jy, pickSqueeze: $y } = l(["inhabit", "pickSqueeze"], function(t, e) {
      return F(t, e, false).squeezeJoin();
    }));
    ({ inhabitmod: Ny, pickmodSqueeze: Ly } = l(["inhabitmod", "pickmodSqueeze"], function(t, e) {
      return F(t, e, true).squeezeJoin();
    }));
    Ry = (t, e) => (e = e.map(d), e.length == 0 ? q : t.fmap((n) => {
      const s = bt(Math.round(n), e.length);
      return e[s];
    }).squeezeJoin());
    bf = class {
      constructor({ onTrigger: e, onToggle: n, getTime: s }) {
        this.started = false, this.cps = 0.5, this.getTime = s, this.time_at_last_tick_message = 0, this.collator = new _n({ getTargetClockTime: s }), this.onToggle = n, this.latency = 0.1, this.cycle = 0, this.id = Math.round(Date.now() * Math.random()), this.worker = new SharedWorker(new URL(
          /* @vite-ignore */
          "" + new URL("assets/clockworker-ZDiUtESR.js", import.meta.url).href,
          import.meta.url
        )), this.worker.port.start(), this.channel = new BroadcastChannel("strudeltick");
        const r = (i) => {
          const { cps: a, begin: u, end: p, cycle: h, time: y } = i;
          this.cps = a, this.cycle = h;
          const g = this.collator.calculateOffset(y) + y;
          o(u, p, g), this.time_at_last_tick_message = g;
        }, o = (i, a, u) => {
          if (this.started === false)
            return;
          this.pattern.queryArc(i, a, { _cps: this.cps, cyclist: "neocyclist" }).forEach((h) => {
            if (h.hasOnset()) {
              const g = Kt(h.whole.begin - this.cycle, this.cps) + u + this.latency, v = Kt(h.duration, this.cps);
              e?.(h, 0, v, this.cps, g);
            }
          });
        };
        this.channel.onmessage = (i) => {
          if (!this.started)
            return;
          const { payload: a, type: u } = i.data;
          switch (u) {
            case "tick":
              r(a);
          }
        };
      }
      sendMessage(e, n) {
        this.worker.port.postMessage({ type: e, payload: n, id: this.id });
      }
      now() {
        const e = (this.getTime() - this.time_at_last_tick_message) * this.cps;
        return this.cycle + e;
      }
      setCps(e = 1) {
        this.sendMessage("cpschange", { cps: e });
      }
      setCycle(e) {
        this.sendMessage("setcycle", { cycle: e });
      }
      setStarted(e) {
        this.sendMessage("toggle", { started: e }), this.started = e, this.onToggle?.(e);
      }
      start() {
        E("[cyclist] start"), this.setStarted(true);
      }
      stop() {
        E("[cyclist] stop"), this.collator.reset(), this.setStarted(false);
      }
      setPattern(e, n = false) {
        this.pattern = e, n && !this.started && this.start();
      }
      log(e, n, s) {
        const r = s.filter((o) => o.hasOnset());
        console.log(`${e.toFixed(4)} - ${n.toFixed(4)} ${Array(r.length).fill("I").join("")}`);
      }
    };
    Sf = ({ getTime: t, defaultOutput: e }) => async (n, s, r, o, i) => {
      try {
        (!n.context.onTrigger || !n.context.dominantTrigger) && await e(n, s, r, o, i), n.context.onTrigger && await n.context.onTrigger(n, t(), o, i);
      } catch (a) {
        zt(a, "getTrigger");
      }
    };
    j = (t) => {
      const e = (n) => [new S(void 0, n.span, t(n.span.begin, n.controls))];
      return new f(e);
    };
    qt = j((t) => t % 1);
    Se = qt.toBipolar();
    Rt = j((t) => 1 - t % 1);
    Ae = Rt.toBipolar();
    Te = j((t) => Math.sin(Math.PI * 2 * t));
    Af = Te.fromBipolar();
    Qy = Af._early(m(1).div(4));
    Uy = Te._early(m(1).div(4));
    Tf = j((t) => Math.floor(t * 2 % 2));
    Xy = Tf.toBipolar();
    Ky = N(qt, Rt);
    Yy = N(Se, Ae);
    Zy = N(Rt, qt);
    tw = N(Ae, Se);
    ew = j(ot);
    Wt = 0;
    Ft = 0;
    typeof window < "u" && document.addEventListener("mousemove", (t) => {
      Wt = t.clientY / document.body.clientHeight, Ft = t.clientX / document.body.clientWidth;
    });
    nw = j(() => Wt);
    sw = j(() => Wt);
    rw = j(() => Ft);
    ow = j(() => Ft);
    Cf = (t) => (t |= 0, t ^= t >>> 16, t = Math.imul(t, 2246822507), t ^= t >>> 13, t = Math.imul(t, 3266489909), t ^= t >>> 16, t >>> 0);
    xf = (t) => Math.floor(t * 536870912);
    Bf = (t, e = 0, n = 0) => {
      const s = t >>> 0 >>> 0, r = Math.floor(t / 4294967296) >>> 0;
      let o = s ^ Math.imul(r ^ 2246822507, 3266489909);
      return o ^= Math.imul(e ^ 2135587861, 2654435769), o ^= Math.imul(n ^ 374761393, 668265261), o >>> 0;
    };
    ne = (t, e = 0, n = 0) => Cf(Bf(t, e, n)) / 4294967296;
    Of = (t, e, n = 0) => {
      const s = xf(t);
      if (e === 1)
        return ne(s, 0, n);
      const r = new Array(e);
      for (let o = 0; o < e; o++) r[o] = ne(s, o, n);
      return r;
    };
    Ce = (t) => {
      const e = t << 13 ^ t, n = e >> 17 ^ e;
      return n << 5 ^ n;
    };
    zf = (t) => t - Math.trunc(t);
    Mf = (t) => Ce(Math.trunc(zf(t / 300) * 536870912));
    se = (t) => t % 536870912 / 536870912;
    Pf = (t, e) => {
      if (e === 1)
        return Math.abs(se(t));
      const n = [];
      for (let s = 0; s < e; s++)
        n.push(se(t)), t = Ce(t);
      return n;
    };
    Ef = (t, e) => Pf(Mf(t), e);
    xe = "legacy";
    K = (t, e = 1, n = 0) => xe === "legacy" ? Ef(t + n, e) : Of(t, e, n);
    cw = (t = "legacy") => xe = t;
    jf = (t) => qt.range(0, t).round().segment(t);
    iw = (t) => {
      const e = d(t).log2(0).floor().add(1);
      return Jf(t, e);
    };
    Jf = (t, e = 16) => {
      e = d(e);
      const n = jf(e).mul(-1).add(e.sub(1));
      return d(t).segment(e).brshift(n).band(C(1));
    };
    uw = (t) => {
      const e = d(t).log2(0).floor().add(1);
      return $f(t, e);
    };
    $f = (t, e = 16) => d(t).withValue((n) => (s) => {
      const r = [];
      for (let o = s - 1; o >= 0; o--)
        r.push(n >> o & 1);
      return r;
    }).appLeft(d(e));
    aw = (t) => j((e) => (n) => K(e, n).map(Math.abs)).appLeft(d(t));
    Nf = (t) => j((e, n) => {
      const r = K(e.floor().add(0.5), t, n.randSeed).map((i, a) => [i, a]).sort((i, a) => (i[0] > a[0]) - (i[0] < a[0])).map((i) => i[1]), o = e.cyclePos().mul(t).floor() % t;
      return r[o];
    })._segment(t);
    Be = (t, e, n) => {
      const s = [...Array(e).keys()].map((r) => n.zoom(m(r).div(e), m(r + 1).div(e)));
      return t.fmap((r) => s[r].repeatCycles(e)._fast(e)).innerJoin();
    };
    lw = l("shuffle", (t, e) => Be(Nf(t), t, e));
    pw = l("scramble", (t, e) => Be(ze(t)._segment(t), t, e));
    Lf = (t, e) => new f((n) => {
      let { randSeed: s, ...r } = n.controls;
      return s = t(s), e.query(n.setControls({ ...r, randSeed: s }));
    }, e._steps);
    fw = l("seed", (t, e) => Lf(() => t, e));
    W = j((t, e) => K(t, 1, e.randSeed));
    hw = W.toBipolar();
    Oe = (t) => W.fmap((e) => e < t);
    dw = (t) => d(t).fmap(Oe).innerJoin();
    mw = Oe(0.5);
    ze = (t) => W.fmap((e) => Math.trunc(e * t));
    yw = (t) => d(t).fmap(ze).innerJoin();
    Me = (t, e) => (e = e.map(d), e.length == 0 ? q : t.range(0, e.length).fmap((n) => {
      const s = Math.min(Math.max(Math.floor(n), 0), e.length - 1);
      return e[s];
    }));
    It = (t, e) => Me(t, e).outerJoin();
    Pe = (t, e) => Me(t, e).innerJoin();
    Rf = (...t) => It(W, t);
    ww = (...t) => Pe(W, t);
    gw = Rf;
    f.prototype.choose = function(...t) {
      return It(this, t);
    };
    f.prototype.choose2 = function(...t) {
      return It(this.fromBipolar(), t);
    };
    Wf = (...t) => Pe(W.segment(1), t);
    bw = Wf;
    Ee = function(t, ...e) {
      const n = e.map((a) => d(a[0])), s = [];
      let r = C(0);
      for (const a of e)
        r = r.add(a[1]), s.push(r);
      const o = En(s), i = function(a) {
        const u = r.mul(a);
        return o.fmap((p) => (h) => n[p.findIndex((y) => y > h, p)]).appLeft(u);
      };
      return t.bind(i);
    };
    Ff = (...t) => Ee(...t).outerJoin();
    _w = (...t) => Ff(W, ...t);
    If = (...t) => Ee(W.segment(1), ...t).innerJoin();
    vw = If;
    kw = j((t, e) => Vf(t, e.randSeed));
    qw = j((t, e) => Hf(t, e.randSeed));
    Sw = l(
      "degradeByWith",
      (t, e, n) => n.fmap((s) => (r) => s).appLeft(t.filterValues((s) => s > e)),
      true,
      true
    );
    Aw = l(
      "degradeBy",
      function(t, e) {
        return e._degradeByWith(W, t);
      },
      true,
      true
    );
    Tw = l("degrade", (t) => t._degradeBy(0.5), true, true);
    Cw = l(
      "undegradeBy",
      function(t, e) {
        return e._degradeByWith(
          W.fmap((n) => 1 - n),
          t
        );
      },
      true,
      true
    );
    xw = l("undegrade", (t) => t._undegradeBy(0.5), true, true);
    Bw = l("sometimesBy", function(t, e, n) {
      return d(t).fmap((s) => z(n._degradeBy(s), e(n._undegradeBy(1 - s)))).innerJoin();
    });
    Ow = l("sometimes", function(t, e) {
      return e._sometimesBy(0.5, t);
    });
    zw = l("someCyclesBy", function(t, e, n) {
      return d(t).fmap(
        (s) => z(
          n._degradeByWith(W._segment(1), s),
          e(n._degradeByWith(W.fmap((r) => 1 - r)._segment(1), 1 - s))
        )
      ).innerJoin();
    });
    Mw = l("someCycles", function(t, e) {
      return e._someCyclesBy(0.5, t);
    });
    Pw = l("often", function(t, e) {
      return e.sometimesBy(0.75, t);
    });
    Ew = l("rarely", function(t, e) {
      return e.sometimesBy(0.25, t);
    });
    jw = l("almostNever", function(t, e) {
      return e.sometimesBy(0.1, t);
    });
    Jw = l("almostAlways", function(t, e) {
      return e.sometimesBy(0.9, t);
    });
    $w = l("never", function(t, e) {
      return e;
    });
    Nw = l("always", function(t, e) {
      return t(e);
    });
    Lw = l("whenKey", function(t, e, n) {
      return n.when(je(t), e);
    });
    Rw = l("keyDown", function(t) {
      return t.fmap(je);
    });
    Ww = new f(function(t) {
      return [new S(void 0, t.span, t.span.duration)];
    });
    Df = new f(function(t) {
      return [new S(void 0, t.span, m(1).div(t.span.duration))];
    });
    Fw = Df;
    Iw = new f(function(t) {
      const e = m(1).div(t.span.duration);
      return [new S(void 0, t.span, Math.log(e) / Math.log(2) + 1)];
    });
    try {
      wt = window?.speechSynthesis;
    } catch {
      console.warn("cannot use window: not in browser?");
    }
    re = wt?.getVoices();
    Vw = l("speak", function(t, e, n) {
      return n.onTrigger((s) => {
        Gf(s.value, t, e);
      });
    });
    Hw = function(t, e = {}) {
      const n = document.getElementById("code"), s = "background-image:url(" + t + ");background-size:contain;";
      n.style = s;
      const { className: r } = n, o = (u, p) => {
        ({
          style: () => n.style = s + ";" + p,
          className: () => n.className = p + " " + r
        })[u]();
      }, i = Object.entries(e).filter(([u, p]) => typeof p == "function");
      Object.entries(e).filter(([u, p]) => typeof p == "string").forEach(([u, p]) => o(u, p)), i.length;
    };
    Dw = () => {
      const t = document.getElementById("code");
      t && (t.style = "");
    };
    E("\u{1F300} @strudel/core loaded \u{1F300}");
    globalThis._strudelLoaded && console.warn(
      `@strudel/core was loaded more than once...
This might happen when you have multiple versions of strudel installed. 
Please check with "npm ls @strudel/core".`
    );
    globalThis._strudelLoaded = true;
  }
});

// outputs/skycam/labs/strudel/study-radio.mjs
console.log = (...args) => console.error(...args);
var { pure, stack, sequence } = await Promise.resolve().then(() => (init_dist2(), dist_exports));
var seed = Number(process.argv[2]);
var song = Number(process.argv[3]);
var options = JSON.parse(process.argv[4]);
if (!Number.isInteger(seed) || seed < 0 || seed > 2147483647 || !Number.isInteger(song) || song < 0) throw Error("Invalid sequence");
var state = (seed ^ Math.imul(song + 1, 2654435761)) >>> 0;
var rand = () => {
  state = Math.imul(state, 1664525) + 1013904223 >>> 0;
  return state / 4294967296;
};
var key = ((seed % 12 + song * 5 + options.transpose) % 12 + 12) % 12;
var scale = [0, 2, 3, 5, 7, 8, 10];
var pitch = (d2) => 60 + key + scale[(d2 % 7 + 7) % 7] + 12 * Math.floor(d2 / 7);
var changes = [[0, 3, 5, 4], [0, 5, 1, 4], [3, 6, 2, 4], [0, 2, 5, 3], [5, 1, 4, 0], [0, 6, 5, 4], [3, 1, 4, 0], [5, 6, 0, 3]];
var progression = changes[(seed + song) % changes.length];
var bridge = changes[(seed + song + 3) % changes.length];
var release = changes[(seed + song + 5) % changes.length];
var swing = options.swing;
var motif = Array.from({ length: 16 }, () => Math.floor(rand() * 7));
var palette = song % 3;
var keysKind = ["piano", "rhodes", "piano"][palette];
var previous = [55, 58, 62, 65];
var bars = [];
for (let bar = 0; bar < 64; bar++) {
  const section = Math.floor(bar / 8), soft = section === 0 || section === 6 || section === 7;
  const progressionHere = [3, 5].includes(section) ? bridge : section === 6 ? release : progression;
  const degree = progressionHere[Math.floor(bar / 2) % 4];
  const intervals = degree === 4 ? [4, 7, 10, 14] : degree === 1 ? [3, 6, 10, 14] : [2, 5, 6].includes(degree) ? [4, 7, 11, 14] : [3, 7, 10, 14];
  const notes = intervals.map((n) => pitch(degree) + n);
  const choices = notes.map((_, inv) => {
    let v = [...notes.slice(inv), ...notes.slice(0, inv).map((n) => n + 12)].sort((a, b) => a - b);
    while (v.reduce((a, b) => a + b) / 4 > 65) v = v.map((n) => n - 12);
    return v;
  });
  const chord = choices.sort((a, b) => a.reduce((s, n, i) => s + Math.abs(n - previous[i]), 0) - b.reduce((s, n, i) => s + Math.abs(n - previous[i]), 0))[0];
  previous = chord;
  const events2 = [];
  const add2 = (pos, kind, note, gain, pan = 0, duration = 3) => events2.push(pure({ kind, note, gain, pan, duration }).compress(pos / 4, Math.min(0.9999, (pos + 0.02) / 4)));
  const hits = bar % 2 ? [0.09, 2 + swing] : [0.045];
  for (const pos of hits) chord.forEach((n, i) => add2(pos + i * 0.014, keysKind, n, (soft ? 0.052 : 0.064) * (0.88 + rand() * 0.18), (i - 1.5) * 0.13, 5.4));
  if (bar % 2 === 0) for (const i of [0, 2]) add2(0.02, "bed", chord[i], 7e-3, (i - 1) * 0.2, 7.8);
  let root = pitch(degree) - 24;
  while (root > 47) root -= 12;
  for (const [pos, interval, len] of [[0.025, 0, 1.65], [2.05, 0, 1.1], [3 + swing, bar % 4 === 3 ? 7 : 12, 0.32]]) {
    if (interval && (soft || rand() > 0.6)) continue;
    add2(pos, "bass", root + interval, 0.14, 0, len * 60 / options.bpm);
  }
  if (section !== 0 || bar >= 4) {
    const rhythm = bar % 2 ? [0.2, 2 + swing] : [0.16, 1 + swing, 3.15];
    rhythm.forEach((pos, j2) => {
      if (rand() > options.melody * (soft ? 0.55 : 1)) return;
      let d2 = j2 === 0 ? degree + [0, 2, 4][bar % 3] : motif[(bar % 4 * 4 + j2 + section) % 16];
      if (section === 5) d2 = 6 - d2;
      let n = j2 === 0 ? pitch(degree) + intervals[bar % 4] : pitch(d2);
      if (degree === 4 && (n - key + 120) % 12 === 10) n += 1;
      while (n > 76) n -= 12;
      while (n < 60) n += 12;
      const kind = palette === 0 ? "flute" : palette === 1 ? "guitar" : "rhodes";
      add2(pos, kind, n, 0.034 * (0.85 + rand() * 0.2), -0.16, 2.4);
      if (pos + 0.75 < 3.95) add2(pos + 0.75, kind, n, 7e-3, 0.28, 2.4);
    });
  }
  const kicks = [[0, 1 + swing, 2.5], [0, 2, 3 + swing], [0, 0.75, 2 + swing]][(Math.floor(bar / 2) + song) % 3];
  kicks.forEach((p, i) => {
    if (i === 0 || rand() < options.density) add2(p, "drum", 0, soft ? 0.16 : 0.21, 0, 1);
  });
  [1.035, 3.035].forEach((p) => add2(p, "drum", 1, soft ? 0.085 : 0.115, 0.06, 1));
  if (!soft && bar % 4 === 3 && rand() < options.density) add2(2 + swing, "drum", 1, 0.025, -0.08, 1);
  for (let eighth = 0; eighth < 8; eighth++) {
    if (eighth % 2 && rand() > options.density * (soft ? 0.6 : 1)) continue;
    add2(Math.floor(eighth / 2) + (eighth % 2 ? swing : 0) + rand() * 0.012, "drum", 3, (eighth % 2 ? 0.016 : 0.025) * (0.8 + rand() * 0.3), -0.2, 1);
  }
  if (bar % 4 === 2 && rand() < options.density) add2(3 + swing, "drum", 4, 0.018, 0.22, 1);
  if (bar % 8 === 7) add2(3.77, "drum", 5, 0.017, 0.1, 1);
  bars.push(stack(...events2));
}
var pattern = sequence(...bars).slow(64);
var events = pattern.queryArc(0, 64).filter((h) => h.hasOnset()).map((h) => ({ beat: Number(h.whole.begin) * 4, ...h.value })).sort((a, b) => a.beat - b.beat);
process.stdout.write(JSON.stringify({ key, palette, events }));
