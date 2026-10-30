import numpy as np
import pytest

from app.algorithms.neural_risk import NeuralRiskModel, metrics, validate_features
from app.repositories.risk_repository import load_bundle, save_bundle
from app.services.neural_risk_service import prepare, split_indices, train_from_csv
from scripts.generate_risk_demo import generate


def test_network_learns_and_round_trips():
    rng = np.random.default_rng(7)
    x = np.column_stack([rng.uniform(10, 95, 120), rng.uniform(.2, 1, 120), rng.uniform(10, 95, 120), rng.uniform(10, 30, 120)])
    y = (x[:, 2] < 50).astype(int)
    model = NeuralRiskModel().fit(x[:80], y[:80], x[80:100], y[80:100], epochs=400)
    assert model.history[-1]['train_loss'] < model.history[0]['train_loss']
    assert metrics(y[100:], model.predict_proba(x[100:]))['f1'] > .7
    restored = NeuralRiskModel.from_dict(model.to_dict())
    np.testing.assert_allclose(restored.predict_proba(x[100:]), model.predict_proba(x[100:]))
    np.testing.assert_allclose(model.mean, x[:80].mean(axis=0))


@pytest.mark.parametrize('values', [[70, np.nan, 60, 20], [70, 80, 60, 20], [70, .8, 60, -1], [70, .8], [101, .8, 60, 20]])
def test_invalid_features(values):
    with pytest.raises(ValueError):
        validate_features(values)


def test_untrained_model_fails_clearly():
    with pytest.raises(ValueError, match='Train'):
        NeuralRiskModel().predict_proba([70, .8, 60, 20])


def test_splits_disjoint_and_reproducible():
    y = np.array([0, 1] * 60)
    splits = split_indices(y)
    assert len(set(np.concatenate(splits))) == len(y)
    assert set(splits[0]).isdisjoint(splits[1])
    for a, b in zip(splits, split_indices(y)):
        np.testing.assert_array_equal(a, b)
        assert set(y[a]) == {0, 1}


def test_training_pipeline_and_repository(tmp_path):
    csv_path, path = tmp_path/'snapshots.csv', tmp_path/'model.json'
    generate(csv_path, count=100)
    bundle = train_from_csv(csv_path, path, data_kind='synthetic', source='Unit-test simulation')
    assert bundle['data_kind'] == 'synthetic'
    assert sum(bundle['split_counts'].values()) == 100
    assert load_bundle(path)['results'] == bundle['results']
    save_bundle(path, bundle)
    assert load_bundle(path)['model_version'] == bundle['model_version']
    assert load_bundle(tmp_path/'missing.json') is None


def test_rejects_duplicate_students_and_future_features(tmp_path):
    from app.repositories.risk_repository import read_snapshots
    path = tmp_path/'snapshots.csv'
    generate(path, count=100)
    rows = read_snapshots(path)
    rows[1]['student_id'] = rows[0]['student_id']
    with pytest.raises(ValueError, match='distinct'):
        prepare(rows)
    rows[1]['student_id'] = 'different'
    rows[0]['snapshot_date'] = rows[0]['outcome_date']
    with pytest.raises(ValueError, match='after'):
        prepare(rows)


def test_confusion_matrix_order():
    assert metrics([0, 0, 1, 1], [.1, .8, .2, .9])['confusion_matrix'] == [[1, 1], [1, 1]]
