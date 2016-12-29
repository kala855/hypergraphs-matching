from __future__ import division
from math import sqrt, pow, exp
import numpy as np
import random
import matplotlib.tri as tri
from numpy import linalg as LA
import cv2
import itertools

# =========================================================================== #


class Hypergraph():
    def __init__(self, kpts, desc):
        self.kpts = kpts
        self.desc = desc
        self.size = len(kpts)
        self.V = [i for i in xrange(len(kpts))]
        self.E = self.__getHyperedges(kpts)
        # self.E = self.__getBfHyperedges()

    def __getHyperedges(self, kpts):
        '''
        builds the hyperedges using the 2 nearest neighbors of each point
        '''
        # E = []
        # n = len(kpts)
        # dist = np.zeros((n, n))
        # W = compute_w_parameter(self.kpts)
        # print "W: ", W
        #
        # for i, r in enumerate(kpts):
        #     for j, l in enumerate(kpts):
        #         dist[i][j] = self.__euclideanDistance(r, l)
        # for i, values in enumerate(dist):
        #     min1, min2 = self.__getMinValues(values, i)
        #     # edge_weigth = hyperedge_weigth((i, min1, min2), 1, self.kpts)
        #     E.append((i, min1, min2))
        #
        # return E
        x, y = zip(*[k.pt for k in kpts])
        triangulation = tri.Triangulation(x, y)

        return triangulation.get_masked_triangles()

    def __getBfHyperedges(self):
        return list(itertools.combinations(range(self.size), 3))

    def __euclideanDistance(self, kpt1, kpt2):
        return sqrt(
            pow(kpt2.pt[0] - kpt1.pt[0], 2) + pow(kpt2.pt[1] - kpt1.pt[1], 2)
        )

    def __getMinValues(self, vec, base):
        '''
        base is the index of the node we want to
        get the 2 minimum values in vec
        '''
        min1, min2 = -1, -1
        minValue = 1e6
        for i, v in enumerate(vec):
            if v < minValue and i != base:
                min1 = i
                minValue = v
        minValue = 1e6
        for i, v in enumerate(vec):
            if v < minValue and i != base and i != min1:
                min2 = i
                minValue = v
        return min1, min2

    def show_hyperedges(self):
        for i, e in enumerate(self.E):
            print "E{0}: {1}".format(i, e)

# =========================================================================== #


def get_features(img, limit=10, outname="sample.jpg", show=False):
    '''
        img should be gray
    '''
    detector = cv2.FeatureDetector_create('SURF')
    descriptor = cv2.DescriptorExtractor_create('SURF')
    kp = detector.detect(img)
    # getting most relevant points
    kp = sorted(kp, key=lambda x: x.response, reverse=True)
    kp, des = descriptor.compute(img, kp)
    img_to_write = np.zeros(img.shape)
    img_to_write = cv2.drawKeypoints(img, kp[:limit], img_to_write)
    cv2.imwrite(outname, img_to_write)
    if show:
        cv2.namedWindow('Keypoints')  # , cv2.WINDOW_NORMAL)
        cv2.imshow('Keypoints', img_to_write)
        cv2.waitKey()
    return (kp[:limit], des[:limit]) if len(kp) > limit else (kp, des)

# =========================== Feature Based Utils =========================== #


def similarity(des1, des2):
    '''
    A measurement of similarity between two Keypoint's descriptors
    '''
    norm1 = LA.norm(des1)
    norm2 = LA.norm(des2)
    similarity = np.dot(des1, des2) / (norm1 * norm2)
    return similarity


def similarity_descriptors(target_descriptors, ref_descriptors):
    n = len(target_descriptors)
    m = len(ref_descriptors)
    dist = np.zeros((n, m))
    for i, t in enumerate(target_descriptors):
        for j, r in enumerate(ref_descriptors):
            dist[i][j] = similarity(t, r)
            # print "similarity between {} and {}".format(i, j), dist[i][j]
    return dist

# =========================================================================== #


def hyperedge_weigth(edge, W, kpts):
    '''
    det([vi - vk, vj - vk]) * sum 1 / sqrt(norm((vi - vk) * norm(vj - vk)))
    '''
    vi = np.asarray(kpts[edge[0]].pt)
    vj = np.asarray(kpts[edge[1]].pt)
    vk = np.asarray(kpts[edge[2]].pt)
    mat = np.array([vi - vk, vj - vk])
    U = LA.det(mat)
    weigth = U * W
    return weigth


def compute_w_parameter(kpts):
    acum = 0
    for i in kpts:
        for j in kpts:
            for k in kpts:
                vi = np.asarray(i.pt)
                vj = np.asarray(j.pt)
                vk = np.asarray(k.pt)
                if vi.all() != vk.all() and vj.all() != vk.all():
                    # TODO FIX division
                    acum += 1 / sqrt(LA.norm(vi - vk) * LA.norm(vj - vk))
    return acum

# ========================== Similarities =============================== #


def vectors_sin(pivot, p, q):
    V1 = np.subtract(p, pivot)
    V2 = np.subtract(q, pivot)
    dot = np.dot(V1, V2)
    angle = np.arccos(dot / (LA.norm(V1) * LA.norm(V2)))
    return np.sin(angle)


def get_angles_sin(edge, kpts):  # TODO fix the nan values
    p1, p2, p3 = kpts[edge[0]].pt, kpts[edge[1]].pt, kpts[edge[2]].pt
    alpha = vectors_sin(p1, p2, p3)  # sin of angle of vectors p2 - p1, p3 - p1
    beta = vectors_sin(p2, p1, p3)  # sin of angle of vectors p1 - p2, p3 - p2
    theta = vectors_sin(p3, p1, p2)  # sin of angle of vectors p1 - p3, p2 - p3

    return [alpha, beta, theta]


def similarity_angles(e1, e2, kpts1, kpts2, sigma=0.5):
    '''
    angles1 and angles2 are those formed by the first and second triangle,
    respecvitly, we'll choose the best case scenario for the sum of sin
    '''

    sin1 = get_angles_sin(e1, kpts1)
    sin2 = get_angles_sin(e2, kpts2)

    perms = itertools.permutations(sin1)
    diffs = [sum(np.abs(np.subtract(s, sin2))) for s in perms]
    min_diff_between_sin = min(diffs)
    similarity = exp(-min_diff_between_sin / sigma)

    return similarity


def similarity_area(e1, e2, kpts1, kpts2, sigma=0.5):
    p = [np.array(kpts1[e1[i]].pt) for i in xrange(3)]
    q = [np.array(kpts2[e2[i]].pt) for i in xrange(3)]

    dp = [
        LA.norm(p[i] - p[j]) for i, j in itertools.combinations(xrange(3), 2)
    ]
    dq = [
        LA.norm(q[i] - q[j]) for i, j in itertools.combinations(xrange(3), 2)
    ]

    sp = sum(dp) / 2
    sq = sum(dq) / 2

    area_p = np.power(sp * (sp - dp[0]) * (sp - dp[1]) * (sp - dp[2]), 1/4)
    area_q = np.power(sq * (sq - dq[0]) * (sq - dq[1]) * (sq - dq[2]), 1/4)
    similarity = exp(-np.abs(area_p - area_q) / sigma)

    # perms = itertools.permutations(dp)
    # diffs = [sum(np.abs(np.subtract(s, dq))) for s in perms]
    # min_diff = min(diffs)
    # similarity = exp(-min_diff / sigma)

    return similarity


def similarity_desc(e1, e2, desc1, desc2, sigma=0.5):
    p = [np.array(desc1[e1[i]]) for i in xrange(3)]
    q = [np.array(desc2[e2[i]]) for i in xrange(3)]

    dp = [
        LA.norm(p[i] - p[j]) for i, j in itertools.combinations(xrange(3), 2)
    ]
    dq = [
        LA.norm(q[i] - q[j]) for i, j in itertools.combinations(xrange(3), 2)
    ]

    perms = itertools.permutations(dp)
    diffs = [sum(np.abs(np.subtract(s, dq))) for s in perms]
    min_diff = min(diffs)
    similarity = exp(-min_diff / sigma)

    return similarity

# ============================ Similarities ================================ #


def match_hyperedges(E1, E2, kpts1, kpts2, desc1, desc2, c1, c2, c3, th):
    '''
    E1, E2: hyperedges lists of img1 and img2, respectly
    '''
    sigma = 0.5
    # indices_taken = []
    matches = []

    s = sum([c1, c2, c3])
    c1 /= s
    c2 /= s
    c3 /= s

    for i, e_i in enumerate(E1):
        best_index = -float('inf')
        max_similarity = -float('inf')
        s_ang = -float('inf')
        s_area = -float('inf')
        s_desc = -float('inf')
        for j, e_j in enumerate(E2):
            sim_dist = similarity_area(e_i, e_j, kpts1, kpts2, sigma)
            sim_angles = similarity_angles(e_i, e_j, kpts1, kpts2, sigma)
            sim_desc = similarity_desc(e_i, e_j, desc1, desc2, sigma)
            similarity = c1 * sim_dist + c2 * sim_angles + c3 * sim_desc

            if similarity > max_similarity:
                best_index = j
                max_similarity = similarity
                s_area = sim_dist
                s_ang = sim_angles
                s_desc = sim_desc
        if max_similarity >= th:
            matches.append(
                (i, best_index, max_similarity, s_area, s_ang, s_desc)
            )
        # indices_taken.append(best_index)
    return matches


def match_points(matches, desc1, desc2, E1, E2):
    matched_points = []
    for mat in matches:
        __queryIdx = mat[0]
        __trainIdx = mat[1]

        p_desc = [np.array(desc1[E1[__queryIdx][i]]) for i in xrange(3)]
        q_desc = [np.array(desc2[E2[__trainIdx][i]]) for i in xrange(3)]

        dist_desc = [[sum(np.abs(q - p)) for q in q_desc] for p in p_desc]
        best_match = [dist.index(min(dist)) for dist in dist_desc]

        for i, j in enumerate(best_match):
            matched_points.append(
                cv2.DMatch(
                    E1[__queryIdx][i], E2[__trainIdx][j], dist_desc[i][j]
                )
            )
    return matched_points


def draw_edges_match(matches, kp1, kp2, E1, E2, img1, img2):
    (rows1, cols1) = img1.shape
    (rows2, cols2) = img2.shape
    out = np.zeros((max([rows1, rows2]), cols1 + cols2, 3), dtype='uint8')

    for mat in matches:
        out[:rows1, :cols1] = np.dstack([img1, img1, img1])
        out[:rows2, cols1:] = np.dstack([img2, img2, img2])
        __queryIdx = mat[0]
        __trainIdx = mat[1]

        (x1_1, y1_1) = kp1[E1[__queryIdx][0]].pt
        (x2_1, y2_1) = kp1[E1[__queryIdx][1]].pt
        (x3_1, y3_1) = kp1[E1[__queryIdx][2]].pt

        (x1_2, y1_2) = kp2[E2[__trainIdx][0]].pt
        (x2_2, y2_2) = kp2[E2[__trainIdx][1]].pt
        (x3_2, y3_2) = kp2[E2[__trainIdx][2]].pt

        cv2.circle(out, (int(x1_1), int(y1_1)), 1, (0, 0, 255), 3)
        cv2.circle(out, (int(x2_1), int(y2_1)), 1, (0, 0, 255), 3)
        cv2.circle(out, (int(x3_1), int(y3_1)), 1, (0, 0, 255), 3)
        cv2.circle(out, (int(x1_2) + cols1, int(y1_2)), 1, (0, 255, 0), 3)
        cv2.circle(out, (int(x2_2) + cols1, int(y2_2)), 1, (0, 255, 0), 3)
        cv2.circle(out, (int(x3_2) + cols1, int(y3_2)), 1, (0, 255, 0), 3)
        print
        print (x1_1, y1_1)
        print (x2_1, y2_1)
        print (x3_1, y3_1)
        print
        print (x1_2, y1_2)
        print (x2_2, y2_2)
        print (x3_2, y3_2)
        print
        print "similarity: {}".format(mat[2])
        print "similarity dist  : {}".format(mat[3])
        print "similarity angles: {}".format(mat[4])
        print "similarity desc  : {}".format(mat[5])

        # cv2.line(out, (int(x1), int(y1)), (int(x2) + cols1, int(y2)),
        # (102, 255, 255), 1)
        # cv2.namedWindow('Matching', cv2.WINDOW_NORMAL)
        cv2.imshow("Matching", out)
        cv2.waitKey()
        cv2.destroyWindow("Matching")
    return out


def draw_points_match(matches, kp1, kp2, img1, img2):
    (rows1, cols1) = img1.shape
    (rows2, cols2) = img2.shape
    out = np.zeros((max([rows1, rows2]), cols1 + cols2, 3), dtype='uint8')
    out[:rows1, :cols1] = np.dstack([img1, img1, img1])
    out[:rows2, cols1:] = np.dstack([img2, img2, img2])
    for mat in matches:
        __queryIdx = mat.queryIdx
        __trainIdx = mat.trainIdx

        (x1, y1) = kp1[__queryIdx].pt
        (x2, y2) = kp2[__trainIdx].pt
        color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255)
        )
        cv2.circle(out, (int(x1), int(y1)), 1, color, 3)
        cv2.circle(out, (int(x2) + cols1, int(y2)), 1, color, 3)
        cv2.line(out, (int(x1), int(y1)), (int(x2) + cols1, int(y2)), color, 1)
    cv2.namedWindow('Matching', cv2.WINDOW_NORMAL)
    cv2.imshow("Matching", out)
    cv2.waitKey()
    cv2.destroyWindow("Matching")


def draw_triangulation(kp, E, img):
    rows, cols = img.shape
    out = np.zeros((rows, cols, 3), dtype='uint8')
    out = np.dstack([img, img, img])
    print E
    for i, j, k in E:
        x1, y1 = kp[i].pt
        x2, y2 = kp[j].pt
        x3, y3 = kp[k].pt

        cv2.circle(out, (int(x1), int(y1)), 8, (0, 0, 255), 1)
        cv2.circle(out, (int(x2), int(y2)), 8, (0, 255, 0), 1)
        cv2.circle(out, (int(x3), int(y3)), 8, (255, 0, 0), 1)

        cv2.line(
            out, (int(x1), int(y1)), (int(x2), int(y2)),
            (102, 255, 255), 1
        )
        cv2.line(
            out, (int(x1), int(y1)), (int(x3), int(y3)),
            (102, 255, 255), 1
        )
        cv2.line(
            out, (int(x3), int(y3)), (int(x2), int(y2)),
            (102, 255, 255), 1
        )
    # cv2.imwrite('./triangulation_gay.png', out)
    cv2.namedWindow('triangulation', cv2.WINDOW_NORMAL)
    cv2.imshow('triangulation', out)
    cv2.waitKey()
    cv2.destroyWindow('triangulation')


if __name__ == "__main__":
    M = 10
    img1 = cv2.imread('./house.seq0.png')
    img2 = cv2.imread('./house.seq0.trans.png')
    # convert to gray
    img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    img2_gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # get features and distances between every pair of points from both images
    (kpts1, des1) = get_features(img1_gray, M, './target.jpg', show=False)
    (kpts2, des2) = get_features(img2_gray, M, './reference.jpg', show=False)

    # distances = similarity_descriptors(des1, des2)
    Hgt = Hypergraph(kpts1, des1)
    Hgr = Hypergraph(kpts2, des2)
    print "Hypergraph construction done"
    # matching
    edge_matches = match_hyperedges(
        Hgt.E, Hgr.E, kpts1, kpts2, des1, des2, 15, 5, 10, 0.85
    )
    print "Hyperedges matching done"

    point_matches = match_points(edge_matches, des1, des2, Hgt.E, Hgr.E)
    # show results
    draw_edges_match(
       edge_matches, kpts1, kpts2, Hgt.E, Hgr.E, img1_gray, img2_gray
    )
    draw_points_match(point_matches, kpts1, kpts2, img1_gray, img2_gray)