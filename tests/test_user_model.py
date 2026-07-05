from app.users.models import User


def test_user_model_definition() -> None:
    assert User.__tablename__ == "users"
    cols = {c.name for c in User.__table__.columns}
    assert {
        "id",
        "email",
        "hashed_password",
        "full_name",
        "is_active",
        "is_superuser",
        "created_at",
        "updated_at",
    } <= cols
    assert User.__table__.columns["email"].unique
