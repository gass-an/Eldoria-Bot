from eldoria.exceptions.base import AppError


def test_app_error_is_exception_root():
    """
    Contrat architectural :
    Toutes les exceptions applicatives doivent héiter de AppError,
    et AppError doit lui-même héiter de Exception.
    """
    assert issubclass(AppError, Exception)
