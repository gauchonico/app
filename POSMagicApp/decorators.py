from django.http import HttpResponse
from django.shortcuts import redirect

def unauthenticated_user(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('DjangoHUDApp:index')
        else:
            return view_func(request, *args, **kwargs)
    return wrapper_func

def allowed_users(allowed_roles=[]):
  def decorator(view_func):
    def wrapper_func(request, *args, **kwargs):
      if request.user.is_anonymous:
        return redirect('login')  # Redirect to login for anonymous users

      user_groups = request.user.groups.all()  # Get all user groups
      authorized = any(group.name in allowed_roles for group in user_groups)

      if authorized:
        return view_func(request, *args, **kwargs)
      else:
        return HttpResponse('You are not authorized to view this page')
    return wrapper_func
  return decorator