import math

from app.services.embeddings import cosine_similarity


def test_identical_vectors_have_similarity_one():
    v = [0.5, 0.5, 0.7071]
    assert math.isclose(cosine_similarity(v, v), 1.0, rel_tol=1e-6)


def test_orthogonal_vectors_have_similarity_zero():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert math.isclose(cosine_similarity(a, b), 0.0, abs_tol=1e-9)


def test_opposite_vectors_have_similarity_negative_one():
    a = [1.0, 0.0]
    b = [-1.0, 0.0]
    assert math.isclose(cosine_similarity(a, b), -1.0, rel_tol=1e-6)


def test_scaling_does_not_change_similarity():
    a = [1.0, 2.0, 3.0]
    b = [2.0, 4.0, 6.0]  # same direction, different magnitude
    assert math.isclose(cosine_similarity(a, b), 1.0, rel_tol=1e-6)


def test_zero_vector_returns_zero_instead_of_crashing():
    a = [0.0, 0.0, 0.0]
    b = [1.0, 2.0, 3.0]
    assert cosine_similarity(a, b) == 0.0
