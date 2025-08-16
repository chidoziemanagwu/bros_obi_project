from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import FileResponse, HttpResponseForbidden
from .models import StaffProfile
from django.contrib.auth import logout
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
import csv
from .forms import ProductForm, StaffUserForm
from .models import Product, Sale
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .forms import ManagerUserUpdateForm
from django.db import transaction
from django.db.models import F, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta

@login_required
def staff_password_change(request):
    # Restrict to staff (not managers)
    try:
        role = request.user.staffprofile.role
    except StaffProfile.DoesNotExist:
        role = 'staff'  # If no profile, treat as staff

    if role != 'staff':
        return HttpResponseForbidden("Only staff can use this page.")

    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keep logged in
            messages.success(request, "Password changed successfully.")
            return redirect('staff_dashboard')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'staff/password_change.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('/')  # Redirect to login page


def landing_login(request):
    if request.user.is_authenticated:
        try:
            profile = request.user.staffprofile
            if profile.role == 'manager':
                return redirect('/staff/manager/dashboard/')
            else:
                return redirect('/staff/dashboard/')
        except StaffProfile.DoesNotExist:
            return redirect('/staff/dashboard/')

    error = None
    if request.method == 'POST':
        raw_identifier = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        user = authenticate(request, username=raw_identifier, password=password)

        if user is not None:
            # User authenticated; now enforce active + profile status
            if not user.is_active:
                error = "Your account is inactive. Please contact your manager."
            else:
                # Optional: also enforce StaffProfile status = active
                try:
                    profile = user.staffprofile
                    if getattr(profile, 'status', 'active') != 'active':
                        error = "Your staff account is not active. Please contact your manager."
                    else:
                        login(request, user)
                        return redirect('/staff/manager/dashboard/' if profile.role == 'manager' else '/staff/dashboard/')
                except StaffProfile.DoesNotExist:
                    # No profile; allow login for now, or decide policy
                    login(request, user)
                    return redirect('/staff/dashboard/')
        else:
            # Fallback check: if identifier is a username or email for an inactive/suspended account, show specific message
            try:
                u = (User.objects.filter(username__iexact=raw_identifier).first()
                     or User.objects.filter(email__iexact=raw_identifier).first())
                if u:
                    if not u.is_active:
                        error = "Your account is inactive. Please contact your manager."
                    else:
                        # Check StaffProfile status as well (even if password was wrong)
                        try:
                            sp = u.staffprofile
                            if getattr(sp, 'status', 'active') != 'active':
                                error = "Your staff account is not active. Please contact your manager."
                            else:
                                error = "Invalid username or password"
                        except StaffProfile.DoesNotExist:
                            error = "Invalid username or password"
                else:
                    error = "Invalid username or password"
            except Exception:
                error = "Invalid username or password"

    return render(request, 'landing.html', {'error': error})


from datetime import timedelta
from django.db.models import Sum
from django.utils import timezone

@login_required
def staff_dashboard(request):
    now = timezone.now()
    start_today = now.astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    end_today = start_today + timedelta(days=1)

    month_start = now.astimezone().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    month_end = next_month

    today_qs = Sale.objects.filter(sold_by=request.user, created_at__gte=start_today, created_at__lt=end_today)
    month_qs = Sale.objects.filter(sold_by=request.user, created_at__gte=month_start, created_at__lt=month_end)

    today_aggs = today_qs.aggregate(total_amount=Sum('total_price'), total_items=Sum('quantity'))
    month_aggs = month_qs.aggregate(total_amount=Sum('total_price'))

    last_sale = Sale.objects.filter(sold_by=request.user).select_related('product').order_by('-created_at').first()
    recent_sales = (Sale.objects
                    .filter(sold_by=request.user)
                    .select_related('product', 'sold_by')
                    .order_by('-created_at')[:5])

    context = {
        'today_total_amount': today_aggs['total_amount'] or 0,
        'today_total_items': today_aggs['total_items'] or 0,
        'month_total_amount': month_aggs['total_amount'] or 0,
        'last_sale': last_sale,
        'recent_sales': recent_sales,
    }
    return render(request, 'staff/dashboard.html', context)




@login_required
def manager_dashboard(request):
    if not hasattr(request.user, 'staffprofile') or request.user.staffprofile.role != 'manager':
        return HttpResponseForbidden("You are not authorized to view this page.")
    return render(request, 'staff/manager/manager_dashboard.html')

def manager_register(request):
    error = None
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        if User.objects.filter(username=username).exists():
            error = "Username already exists"
        else:
            user = User.objects.create_user(username=username, password=password)
            StaffProfile.objects.create(user=user, role='manager')
            login(request, user)
            return redirect('/staff/manager/dashboard/')
    return render(request, 'manager_register.html', {'error': error})




def manager_required(view_func):
    def _wrapped(request, *args, **kwargs):
        if not hasattr(request.user, 'staffprofile') or request.user.staffprofile.role != 'manager':
            return HttpResponseForbidden("You are not authorized to view this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped

@login_required
def products_list(request):
    # both staff and manager can view products; managers see extra actions
    q = request.GET.get('q', '')
    qs = Product.objects.all().order_by('name')
    if q:
        qs = qs.filter(name__icontains=q)
    context = {'products': qs, 'query': q}
    return render(request, 'products/product_list.html', context)

@login_required
@manager_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES or None)
        if form.is_valid():
            form.save()
            messages.success(request, "Product created.")
            return redirect('products_list')
    else:
        form = ProductForm()
    return render(request, 'products/form.html', {'form': form, 'title': 'Add Product'})

@login_required
@manager_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES or None, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated.")
            return redirect('products_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'products/form.html', {'form': form, 'title': 'Edit Product'})

@login_required
@manager_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, "Product deleted.")
        return redirect('products_list')
    return render(request, 'products/confirm_delete.html', {'object': product, 'type': 'Product'})

# Staff management (manager only)
@login_required
@manager_required
def staff_list(request):
    qs = User.objects.filter(staffprofile__isnull=False).order_by('username')
    return render(request, 'staff/list.html', {'staff': qs})

@login_required
@manager_required
def staff_create(request):
    if request.method == 'POST':
        form = StaffUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            pwd = form.cleaned_data.get('password')
            if pwd:
                user.set_password(pwd)
            user.save()
            # create staff profile; default role = staff
            StaffProfile.objects.create(user=user, role='staff')
            messages.success(request, "Staff user created.")
            return redirect('staff_list')
    else:
        form = StaffUserForm()
    return render(request, 'staff/form.html', {'form': form, 'title': 'Add Staff'})

@login_required
@manager_required
def staff_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = StaffUserForm(request.POST, instance=user)
        if form.is_valid():
            u = form.save(commit=False)
            pwd = form.cleaned_data.get('password')
            if pwd:
                u.set_password(pwd)
            u.save()
            messages.success(request, "Staff user updated.")
            return redirect('staff_list')
    else:
        form = StaffUserForm(instance=user)
    return render(request, 'staff/form.html', {'form': form, 'title': 'Edit Staff'})

@login_required
@manager_required
def staff_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.is_active = not user.is_active
    user.save()
    return redirect('staff_list')

@login_required
@manager_required
def sales_history(request):
    qs = Sale.objects.select_related('product', 'sold_by').order_by('-created_at')
    start = request.GET.get('start')
    end = request.GET.get('end')
    q = request.GET.get('q', '').strip()

    if start:
        try:
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            qs = qs.filter(created_at__gte=start_dt)
        except ValueError:
            pass
    if end:
        try:
            end_dt = datetime.strptime(end, '%Y-%m-%d')
            qs = qs.filter(created_at__lte=end_dt)
        except ValueError:
            pass
    if q:
        qs = qs.filter(product__name__icontains=q)

    # Aggregates (for the stats strip)
    aggs = qs.aggregate(
        total_amount=Sum('total_price'),
        total_items=Sum('quantity'),
        sale_count=Count('id'),
    )
    total_amount = aggs['total_amount'] or 0
    total_items = aggs['total_items'] or 0
    sale_count = aggs['sale_count'] or 0
    avg_per_sale = (total_amount / sale_count) if sale_count else 0

    # PDF export (restored)
    if request.GET.get('export') == 'pdf':
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        left = 15 * mm
        right = width - 15 * mm
        top = height - 15 * mm
        bottom = 15 * mm
        y = top

        p.setFont("Helvetica-Bold", 14)
        p.drawString(left, y, "Bros Obi Project — Sales History")
        p.setFont("Helvetica", 9)
        y -= 12
        filters_text = []
        if start: filters_text.append(f"Start: {start}")
        if end: filters_text.append(f"End: {end}")
        if q: filters_text.append(f"Query: {q}")
        subtitle = " | ".join(filters_text) if filters_text else "All records"
        p.drawString(left, y, subtitle)

        y -= 18
        p.setStrokeColor(colors.lightgrey)
        p.line(left, y, right, y)
        y -= 12
        p.setFont("Helvetica-Bold", 9)
        col_x = {
            "date": left,
            "product": left + 35*mm,
            "qty": left + 120*mm,
            "total": left + 140*mm,
            "user": left + 165*mm,
        }
        p.drawString(col_x["date"], y, "Date")
        p.drawString(col_x["product"], y, "Product")
        p.drawRightString(col_x["qty"] + 10*mm, y, "Qty")
        p.drawRightString(col_x["total"] + 15*mm, y, "Total (NGN)")
        p.drawString(col_x["user"], y, "Sold By")
        y -= 8
        p.setStrokeColor(colors.lightgrey)
        p.line(left, y, right, y)
        y -= 12
        p.setFont("Helvetica", 9)

        total_sum = 0
        for s in qs:
            if y < bottom + 30*mm:
                p.showPage()
                y = top
                p.setFont("Helvetica-Bold", 14)
                p.drawString(left, y, "Bros Obi Project — Sales History (cont.)")
                p.setFont("Helvetica", 9)
                y -= 18
                p.setStrokeColor(colors.lightgrey)
                p.line(left, y, right, y)
                y -= 12
                p.setFont("Helvetica-Bold", 9)
                p.drawString(col_x["date"], y, "Date")
                p.drawString(col_x["product"], y, "Product")
                p.drawRightString(col_x["qty"] + 10*mm, y, "Qty")
                p.drawRightString(col_x["total"] + 15*mm, y, "Total (NGN)")
                p.drawString(col_x["user"], y, "Sold By")
                y -= 8
                p.setStrokeColor(colors.lightgrey)
                p.line(left, y, right, y)
                y -= 12
                p.setFont("Helvetica", 9)

            date_str = s.created_at.strftime("%Y-%m-%d %H:%M")
            product_name = (s.product.name[:42] + "…") if len(s.product.name) > 43 else s.product.name
            qty_str = str(s.quantity)
            total_str = f"{s.total_price:,.2f}"
            sold_by = getattr(s.sold_by, "username", "")

            p.drawString(col_x["date"], y, date_str)
            p.drawString(col_x["product"], y, product_name)
            p.drawRightString(col_x["qty"] + 10*mm, y, qty_str)
            p.drawRightString(col_x["total"] + 15*mm, y, total_str)
            p.drawString(col_x["user"], y, sold_by)
            y -= 14

            total_sum += float(s.total_price)

        y -= 6
        p.setStrokeColor(colors.black)
        p.line(col_x["total"] + 15*mm - 40*mm, y, col_x["total"] + 15*mm, y)
        y -= 12
        p.setFont("Helvetica-Bold", 10)
        p.drawRightString(col_x["total"] + 15*mm, y, f"Total: NGN {total_sum:,.2f}")

        p.showPage()
        p.save()
        buffer.seek(0)
        filename = f"sales_history_{timezone.now().date()}.pdf"
        return FileResponse(buffer, as_attachment=True, filename=filename)

    return render(
        request,
        'sales/history.html',
        {
            'sales': qs,
            'start': start,
            'end': end,
            'q': q,
            'total_amount': total_amount,
            'total_items': total_items,
            'sale_count': sale_count,
            'avg_per_sale': avg_per_sale,
        }
    )




@login_required
@manager_required
def manager_profile(request):
    # Assumes every manager has a StaffProfile with role='manager'
    profile = request.user.staffprofile
    context = {
        'profile': profile,
    }
    return render(request, 'staff/manager/profile.html', context)


@login_required
@manager_required
def manager_profile_edit(request):
    user = request.user
    if request.method == 'POST':
        form = ManagerUserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('manager_profile')
    else:
        form = ManagerUserUpdateForm(instance=user)
    return render(request, 'staff/manager/profile_edit.html', {'form': form})

@login_required
@manager_required
def manager_password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keep the user logged in
            messages.success(request, "Password changed successfully.")
            return redirect('manager_profile')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'staff/manager/password_change.html', {'form': form})



@login_required
def sale_create(request):
    # Allow both staff and managers to record a sale
    from .forms import SaleCreateForm  # local import to avoid circulars if any
    if request.method == 'POST':
        form = SaleCreateForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            qty = form.cleaned_data['quantity']

            try:
                with transaction.atomic():
                    # Lock the product row so concurrent sales are safe
                    p = Product.objects.select_for_update().get(pk=product.pk)
                    if p.quantity < qty:
                        messages.error(request, f"Insufficient stock for {p.name}. Available: {p.quantity}.")
                        return redirect('sale_create')

                    # Deduct stock
                    p.quantity = F('quantity') - qty
                    p.save(update_fields=['quantity'])

                    # Create sale; total_price will be normalized in Sale.save()
                    Sale.objects.create(
                        product=p,
                        quantity=qty,
                        total_price=p.price * qty,
                        sold_by=request.user
                    )

                messages.success(request, f"Sale recorded for {product.name} x{qty}. Stock updated.")
                return redirect('sale_create')
            except Product.DoesNotExist:
                messages.error(request, "Selected product does not exist.")
            except Exception:
                messages.error(request, "Could not complete sale. Please try again.")
    else:
        form = SaleCreateForm()

    # Provide products for the template’s priceMap JSON
    products = Product.objects.filter(active=True).order_by('name')
    return render(request, 'sales/create.html', {'form': form, 'products': products})

@login_required
def price_list(request):
    products = Product.objects.filter(active=True).order_by('name')

    # Optional PDF export (uses the same libs you already imported)
    if request.GET.get('export') == 'pdf':
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        left = 20 * mm
        right = width - 20 * mm
        top = height - 20 * mm
        y = top

        p.setFont("Helvetica-Bold", 16)
        p.drawString(left, y, "Bros Obi — Price List")
        y -= 18
        p.setFont("Helvetica", 10)
        p.drawString(left, y, f"Total products: {products.count()}")
        y -= 10
        p.setStrokeColor(colors.lightgrey)
        p.line(left, y, right, y)
        y -= 12
        p.setFont("Helvetica-Bold", 11)
        p.drawString(left, y, "Product")
        p.drawRightString(right, y, "Price (NGN)")
        y -= 10
        p.setStrokeColor(colors.lightgrey)
        p.line(left, y, right, y)
        y -= 14
        p.setFont("Helvetica", 10)

        for prod in products:
            if y < 20 * mm:
                p.showPage()
                y = top
                p.setFont("Helvetica-Bold", 16)
                p.drawString(left, y, "Bros Obi — Price List (cont.)")
                y -= 24
                p.setFont("Helvetica-Bold", 11)
                p.drawString(left, y, "Product")
                p.drawRightString(right, y, "Price (NGN)")
                y -= 10
                p.setStrokeColor(colors.lightgrey)
                p.line(left, y, right, y)
                y -= 14
                p.setFont("Helvetica", 10)

            name = prod.name
            price = f"{prod.price:,.2f}"
            p.drawString(left, y, name[:70] + ("…" if len(name) > 70 else ""))
            p.drawRightString(right, y, price)
            y -= 14

        p.showPage()
        p.save()
        buffer.seek(0)
        from django.http import FileResponse
        return FileResponse(buffer, as_attachment=True, filename="price_list.pdf")

    return render(request, 'products/price_list.html', {'products': products})



@login_required
def staff_sales_history(request):
    qs = Sale.objects.select_related('product', 'sold_by').filter(sold_by=request.user).order_by('-created_at')

    start = request.GET.get('start')
    end = request.GET.get('end')
    q = request.GET.get('q', '').strip()

    if start:
        try:
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            qs = qs.filter(created_at__gte=start_dt)
        except ValueError:
            pass
    if end:
        try:
            end_dt = datetime.strptime(end, '%Y-%m-%d')
            qs = qs.filter(created_at__lte=end_dt)
        except ValueError:
            pass
    if q:
        qs = qs.filter(product__name__icontains=q)

    # Aggregates for the stats strip
    aggs = qs.aggregate(
        total_amount=Sum('total_price'),
        total_items=Sum('quantity'),
        sale_count=Count('id'),
    )
    total_amount = aggs['total_amount'] or 0
    total_items = aggs['total_items'] or 0
    sale_count = aggs['sale_count'] or 0
    avg_per_sale = (total_amount / sale_count) if sale_count else 0

    if request.GET.get('export') == 'pdf':
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        left = 15 * mm
        right = width - 15 * mm
        top = height - 15 * mm
        bottom = 15 * mm
        y = top

        p.setFont("Helvetica-Bold", 14)
        p.drawString(left, y, f"{request.user.username} — Sales History")
        p.setFont("Helvetica", 9)
        y -= 12
        filters_text = []
        if start: filters_text.append(f"Start: {start}")
        if end: filters_text.append(f"End: {end}")
        if q: filters_text.append(f"Query: {q}")
        subtitle = " | ".join(filters_text) if filters_text else "Your records"
        p.drawString(left, y, subtitle)

        y -= 18
        p.setStrokeColor(colors.lightgrey)
        p.line(left, y, right, y)
        y -= 12
        p.setFont("Helvetica-Bold", 9)
        col_x = {
            "date": left,
            "product": left + 35*mm,
            "qty": left + 120*mm,
            "total": left + 140*mm,
        }
        p.drawString(col_x["date"], y, "Date")
        p.drawString(col_x["product"], y, "Product")
        p.drawRightString(col_x["qty"] + 10*mm, y, "Qty")
        p.drawRightString(col_x["total"] + 15*mm, y, "Total (NGN)")
        y -= 8
        p.setStrokeColor(colors.lightgrey)
        p.line(left, y, right, y)
        y -= 12
        p.setFont("Helvetica", 9)

        total_sum = 0
        for s in qs:
            if y < bottom + 30*mm:
                p.showPage()
                y = top
                p.setFont("Helvetica-Bold", 14)
                p.drawString(left, y, f"{request.user.username} — Sales History (cont.)")
                y -= 18
                p.setStrokeColor(colors.lightgrey)
                p.line(left, y, right, y)
                y -= 12
                p.setFont("Helvetica-Bold", 9)
                p.drawString(col_x["date"], y, "Date")
                p.drawString(col_x["product"], y, "Product")
                p.drawRightString(col_x["qty"] + 10*mm, y, "Qty")
                p.drawRightString(col_x["total"] + 15*mm, y, "Total (NGN)")
                y -= 8
                p.setStrokeColor(colors.lightgrey)
                p.line(left, y, right, y)
                y -= 12
                p.setFont("Helvetica", 9)

            date_str = s.created_at.strftime("%Y-%m-%d %H:%M")
            product_name = (s.product.name[:42] + "…") if len(s.product.name) > 43 else s.product.name
            qty_str = str(s.quantity)
            total_str = f"{s.total_price:,.2f}"

            p.drawString(col_x["date"], y, date_str)
            p.drawString(col_x["product"], y, product_name)
            p.drawRightString(col_x["qty"] + 10*mm, y, qty_str)
            p.drawRightString(col_x["total"] + 15*mm, y, total_str)
            y -= 14

            total_sum += float(s.total_price)

        y -= 6
        p.setStrokeColor(colors.black)
        p.line(col_x["total"] + 15*mm - 40*mm, y, col_x["total"] + 15*mm, y)
        y -= 12
        p.setFont("Helvetica-Bold", 10)
        p.drawRightString(col_x["total"] + 15*mm, y, f"Total: NGN {total_sum:,.2f}")

        p.showPage()
        p.save()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f"my_sales_history_{timezone.now().date()}.pdf")

    return render(
        request,
        'sales/history.html',
        {
            'sales': qs,
            'start': start,
            'end': end,
            'q': q,
            'total_amount': total_amount,
            'total_items': total_items,
            'sale_count': sale_count,
            'avg_per_sale': avg_per_sale,
        }
    )