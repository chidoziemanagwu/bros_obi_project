from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from staff.views import manager_required  # reuse your decorator
from .models import NotificationEmail
from .forms import NotificationEmailForm

@login_required
@manager_required
def email_list(request):
    if request.method == 'POST':
        form = NotificationEmailForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Email added to notifications.")
            return redirect('notifications_email_list')
    else:
        form = NotificationEmailForm()
    emails = NotificationEmail.objects.order_by('email')
    return render(request, 'notifications/email_list.html', {'emails': emails, 'form': form})

@login_required
@manager_required
def email_delete(request, pk):
    email = get_object_or_404(NotificationEmail, pk=pk)
    if request.method == 'POST':
        email.delete()
        messages.success(request, "Email removed.")
        return redirect('notifications_email_list')
    # Optional: confirm page; or redirect if no GET confirmation desired
    return render(request, 'notifications/confirm_delete.html', {'object': email, 'type': 'Notification Email'})