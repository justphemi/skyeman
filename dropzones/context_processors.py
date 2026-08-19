"""Global template context — expose brand constants to every template."""
from .models import INSTRUCTOR_NAME


def brand(request):
    """Inject Skyeman brand constants so templates never have to import them."""
    return {"INSTRUCTOR_NAME": INSTRUCTOR_NAME}
