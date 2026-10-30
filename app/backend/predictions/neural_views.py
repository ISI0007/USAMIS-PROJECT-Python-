"""Layer 2: permission checks and HTTP adaptation for the research model."""
from pathlib import Path

from flask import current_app, render_template, request
from flask_login import login_required

from . import bp
from ..security.decorators import permission_required
from ..services.neural_risk_service import load_experiment, predict


@bp.route("/neural", methods=["GET", "POST"])
@login_required
@permission_required("manage_students")
def neural_lab():
    path = current_app.config.get("NEURAL_RISK_ARTIFACT", str(Path(current_app.instance_path) / "neural-risk.json"))
    bundle, result, error = load_experiment(path), None, None
    if request.method == "POST":
        if bundle is None:
            error = "No trained model is available. Run the documented training command first."
        else:
            try:
                values = [float(request.form.get(k, "")) for k in
                          ("prior_average", "attendance_rate", "early_average", "credit_load")]
                result = predict(bundle, values)
            except (ValueError, TypeError) as exc:
                error = str(exc)
    return render_template("predictions/neural.html", bundle=bundle, result=result, error=error), (400 if error else 200)
