from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import SignUpForm


def register(request):
    if request.user.is_authenticated:
        return redirect("tracker:dashboard")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("tracker:dashboard")
    else:
        form = SignUpForm()

    return render(request, "accounts/register.html", {"form": form})
