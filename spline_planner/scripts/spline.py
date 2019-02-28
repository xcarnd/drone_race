import numpy as np


class QuinticSpline(object):
  def __init__(self, p_s, p_e, d1_s, d1_e, d2_s, d2_e):
    # see Sprunk[2008] eq 3.12 & eq 3.13
    p1 = 0.2 * d1_s + p_s
    p4 = p_e - 0.2 * d1_e
    p2 = 0.05 * d2_s + 2 * p1 - p_s
    p3 = 0.05 * d2_e + 2 * p4 - p_e
    self.cm = np.array([
      - p_s + 5 * p1 - 10 * p2 + 10 * p3 - 5 * p4 + p_e,
      5 * p_s - 20 * p1 + 30 * p2 - 20 * p3 + 5 * p4,
      - 10 * p_s + 30 * p1 - 30 * p2 + 10 * p3,
      10 * p_s - 20 * p1 + 10 * p2,
      - 5 * p_s + 5 * p1,
      p_s
    ])

    self.cm_d1 = np.array([
      5 * self.cm[0, :],
      4 * self.cm[1, :],
      3 * self.cm[2, :],
      2 * self.cm[3, :],
          self.cm[4, :]
    ])

    self.cm_d2 = np.array([
      4 * self.cm_d1[0, :],
      3 * self.cm_d1[1, :],
      2 * self.cm_d1[2, :],
          self.cm_d1[3, :]
    ])

  def evaluate(self, t, derivative=0):
    t2 = t ** 2
    t3 = t * t2
    t4 = t2 ** 2
    t5 = t2 * t3
    if derivative == 0:
      return np.matmul(np.array([t5, t4, t3, t2, t, 1], dtype=np.float), self.cm).reshape(-1)
    elif derivative == 1:
      return np.matmul(np.array([t4, t3, t2, t, 1], dtype=np.float), self.cm_d1).reshape(-1)
    else:
      return np.matmul(np.array([t3, t2, t, 1], dtype=np.float), self.cm_d2).reshape(-1)

  def evaluate_with_derivatives(self, t):
    t2 = t ** 2
    t3 = t * t2
    t4 = t2 ** 2
    t5 = t2 * t3
    return np.matmul(np.array([t5, t4, t3, t2, t, 1], dtype=np.float), self.cm).reshape(-1), \
           np.matmul(np.array([t4, t3, t2, t, 1], dtype=np.float), self.cm_d1).reshape(-1), \
           np.matmul(np.array([t3, t2, t, 1], dtype=np.float), self.cm_d2).reshape(-1)

def propose_geometric_spline_path(p1, p2, p3, t1=None, t3=None, a1=None, a3=None):
  """Propose quintic splines given:
  1. start position, intermediate position, end position
  2. tangent (first-order derivative) at start position, tangent at end position
  3. second-order derivative at start position and end position
  """
  # type: (np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray) -> list[QuinticSpline]
  direct12 = p2 - p1
  direct23 = p3 - p2

  # default t1 and t3 is the same as the direction of p1 -> p2 and p2 -> p3. 
  # default a1 and a3 is 0
  if t1 is None:
    t1 = 0.5 * direct12
  if t3 is None:
    t3 = 0.5 * direct23
  if a1 is None:
    a1 = np.array([0, 0, 0], dtype=np.float)
  if a3 is None:
    a3 = np.array([0, 0, 0], dtype=np.float)
  
  norm_12 = np.linalg.norm(direct12)
  norm_23 = np.linalg.norm(direct23)
  t2 = direct12 / norm_12

  axis = np.cross(direct12, direct23)
  axis /= np.linalg.norm(axis)
  angle = np.arccos(np.dot(direct12, direct23) / (norm_12 * norm_23)) / 2
  # by Rodrigues' rotation formula
  t2 = np.cos(angle) * t2 + np.sin(angle) * np.cross(axis, t2) + (1 - np.cos(angle)) * np.dot(axis, t2) * axis
  t2 *= (min(norm_12, norm_23))
  # see Sprunk[2008] ch4.1.2 for reference
  alpha = norm_23 / (norm_12 + norm_23)
  beta = norm_12 / (norm_12 + norm_23)
  a2 = alpha * (6 * p1 + 2 * t1 + 4 * t2 - 6 * p2) + beta * (-6 * p2 - 4 * t2 - 2 * t3 + 6 * p3)

  return [QuinticSpline(p1, p2, t1, t2, a1, a2),
          QuinticSpline(p2, p3, t2, t3, a2, a3)]


def sample_path(path, ds = 0.1, samples_per_seg = 300):
  """Sample points along the given path
  """
  # type: (List[QuinticSpline], float, int) -> List[(double, double), (np.ndarray, np.ndarray, np.ndarray)]
  num_seg = len(path)
  t = np.linspace(0, 1, samples_per_seg)
  samples = []
  for i in range(num_seg):
    for x in t:
      samples.append((x + i, path[i].evaluate_with_derivatives(x)))
  # perform numeric integral to the the approximated curve length
  last_t, (pt, d1, d2) = samples[0]
  last_d1_norm = np.linalg.norm(d1)
  last_s = 0
  
  result = []
  result.append(((0, 0), (pt, d1, d2)))

  s = 0
  for t, (pt, d1, d2) in samples[1:]:
    d1_norm = np.linalg.norm(d1)
    s += (0.5 * (d1_norm + last_d1_norm) * (t - last_t))
    last_d1_norm = d1_norm
    last_t = t

    if s - last_s >= ds:
      last_s = s
      result.append(((s, t), (pt, d1, d2)))

  return result