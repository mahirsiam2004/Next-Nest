# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.exceptions import FieldError
from user.models import Room, House, Contact

from django.views.decorators.csrf import csrf_exempt
import json

User = get_user_model()

def is_admin(user):
    """Check if user is admin or staff"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Main admin dashboard view"""
    # Get statistics
    try:
        # Try to count unchecked contacts if field exists
        unchecked_contacts = Contact.objects.filter(checked=False).count()
    except (FieldError, Exception):
        # If checked field doesn't exist, just count all contacts
        unchecked_contacts = Contact.objects.count()
    
    stats = {
        'total_users': User.objects.count(),
        'total_rooms': Room.objects.count(),
        'total_houses': House.objects.count(),
        'total_contacts': unchecked_contacts,
    }
    
    # Get data for tables - use the correct primary key field names
    users = User.objects.all().order_by('-email')
    rooms = Room.objects.all().order_by('-room_id')
    houses = House.objects.all().order_by('-house_id')
    contacts = Contact.objects.all().order_by('-contact_id')
    
    context = {
        'stats': stats,
        'users': users,
        'rooms': rooms,
        'houses': houses,
        'contacts': contacts,
    }
    
    return render(request, 'admin/dashboard.html', context)

# @login_required
# @user_passes_test(is_admin)
# def add_user(request):
#     """Add new user"""
#     if request.method == 'POST':
#         try:
#             email = request.POST.get('email')
#             full_name = request.POST.get('full_name')
#             password = request.POST.get('password')
#             role = request.POST.get('role', 'user')
            
#             # Check if user already exists
#             if User.objects.filter(email=email).exists():
#                 messages.error(request, 'User with this email already exists.')
#                 return redirect('admin:dashboard')
            
#             # Create user
#             user = User.objects.create(
#                 email=email,
#                 username=email,  # Use email as username
#                 first_name=full_name.split(' ')[0] if full_name else '',
#                 last_name=' '.join(full_name.split(' ')[1:]) if full_name and len(full_name.split(' ')) > 1 else '',
#                 password=make_password(password),
#                 is_active=True,
#             )
            
#             # Set role
#             if role == 'admin':
#                 user.is_staff = True
#                 user.is_superuser = True
#             elif role == 'staff':
#                 user.is_staff = True
            
#             user.save()
            
#             messages.success(request, f'User {email} created successfully.')
            
#         except Exception as e:
#             messages.error(request, f'Error creating user: {str(e)}')
    
#     return redirect('admin:dashboard')

@login_required
@user_passes_test(is_admin)
def delete_user(request, email):
    """Delete user"""
    try:
        user = get_object_or_404(User, email=email)
        
        # Prevent deletion of current user
        if user == request.user:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('admin:dashboard')
        
        user_email = user.email
        user.delete()
        messages.success(request, f'User {user_email} deleted successfully.')
        
    except Exception as e:
        messages.error(request, f'Error deleting user: {str(e)}')
    
    return redirect('admin:dashboard')

@login_required
@user_passes_test(is_admin)
def delete_room(request, room_id):
    """Delete room"""
    try:
        room = get_object_or_404(Room, room_id=room_id)  # Use correct primary key field
        room_location = room.location
        room.delete()
        messages.success(request, f'Apartment {room_location} deleted successfully.')
        
    except Exception as e:
        messages.error(request, f'Error deleting room: {str(e)}')
    
    return redirect('admin:dashboard')

@login_required
@user_passes_test(is_admin)
def delete_house(request, house_id):
    """Delete house"""
    try:
        house = get_object_or_404(House, house_id=house_id)  # Use correct primary key field
        house_location = house.location
        house.delete()
        messages.success(request, f'House at {house_location} deleted successfully.')
        
    except Exception as e:
        messages.error(request, f'Error deleting house: {str(e)}')
    
    return redirect('admin:dashboard')

@login_required
@user_passes_test(is_admin)
def view_contact(request, contact_id):
    """View contact details and mark as checked"""
    try:
        contact = get_object_or_404(Contact, contact_id=contact_id)  # Use correct primary key field
        
        # Mark as checked when viewed (if field exists)
        try:
            if hasattr(contact, 'checked') and not contact.checked:
                contact.checked = True
                contact.save()
        except (FieldError, Exception):
            # Field doesn't exist, skip this step
            pass
        
        context = {
            'contact': contact,
        }
        
        return render(request, 'admin/contact_detail.html', context)
        
    except Exception as e:
        messages.error(request, f'Error viewing contact: {str(e)}')
        return redirect('admin:dashboard')

@login_required
@user_passes_test(is_admin)
def delete_contact(request, contact_id):
    """Delete contact"""
    try:
        contact = get_object_or_404(Contact, contact_id=contact_id)  # Use correct primary key field
        contact_subject = contact.subject
        contact.delete()
        messages.success(request, f'Contact "{contact_subject}" deleted successfully.')
        
    except Exception as e:
        messages.error(request, f'Error deleting contact: {str(e)}')
    
    return redirect('admin:dashboard')

@login_required
@user_passes_test(is_admin)
def toggle_room_verification(request, room_id):
    """Toggle room verification status"""
    if request.method == 'POST':
        try:
            room = get_object_or_404(Room, room_id=room_id)  # Use correct primary key field
            room.verified = not room.verified
            room.save()
            
            status = "verified" if room.verified else "unverified"
            messages.success(request, f'Apartment marked as {status}.')
            
        except Exception as e:
            messages.error(request, f'Error updating Apartment: {str(e)}')
    
    return redirect('admin:dashboard')

@login_required
@user_passes_test(is_admin)
def toggle_house_verification(request, house_id):
    """Toggle house verification status"""
    if request.method == 'POST':
        try:
            house = get_object_or_404(House, house_id=house_id)  # Use correct primary key field
            house.verified = not house.verified
            house.save()
            
            status = "verified" if house.verified else "unverified"
            messages.success(request, f'House marked as {status}.')
            
        except Exception as e:
            messages.error(request, f'Error updating house: {str(e)}')
    
    return redirect('admin:dashboard')

# API Views for AJAX requests (optional)
@login_required
@user_passes_test(is_admin)
def get_stats_api(request):
    """Get dashboard statistics via API"""
    try:
        unchecked_contacts = Contact.objects.filter(checked=False).count()
    except (FieldError, Exception):
        unchecked_contacts = Contact.objects.count()
        
    stats = {
        'total_users': User.objects.count(),
        'total_rooms': Room.objects.count(),
        'total_houses': House.objects.count(),
        'total_contacts': unchecked_contacts,
    }
    return JsonResponse(stats)

@login_required
@user_passes_test(is_admin)
def search_users_api(request):
    """Search users via API"""
    query = request.GET.get('q', '')
    if query:
        users = User.objects.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )[:10]
        
        data = [{
            'id': user.id,
            'email': user.email,
            'name': f"{user.first_name} {user.last_name}".strip(),
            'is_active': user.is_active,
            'role': 'Admin' if user.is_superuser else 'Staff' if user.is_staff else 'User'
        } for user in users]
        
        return JsonResponse({'users': data})
    
    return JsonResponse({'users': []})




# @login_required
# @user_passes_test(is_admin)
# @csrf_exempt
# def update_user_role(request):
#     """AJAX: Update user role (admin/staff)"""
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             email = data.get('email')
#             role_type = data.get('role_type')
#             is_checked = data.get('is_checked')

#             user = get_object_or_404(User, email=email)

#             if role_type == 'admin':
#                 user.is_superuser = is_checked
#             elif role_type == 'staff':
#                 user.is_staff = is_checked
#             user.save()

#             return JsonResponse({'success': True})
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': str(e)})
#     return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@user_passes_test(is_admin)
@csrf_exempt
def update_verification(request):
    """AJAX: Update verification for room or house"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_type = data.get('item_type')
            item_id = data.get('item_id')
            is_verified = data.get('is_verified')

            if item_type == 'room':
                obj = get_object_or_404(Room, room_id=item_id)
            elif item_type == 'house':
                obj = get_object_or_404(House, house_id=item_id)
            else:
                return JsonResponse({'success': False, 'error': 'Invalid item type'})

            obj.verified = is_verified
            obj.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})










@login_required
@user_passes_test(is_admin)
@csrf_exempt
def update_user_role(request):
    """AJAX: Update user role (admin/staff)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            role_type = data.get('role_type')
            is_checked = data.get('is_checked')

            user = get_object_or_404(User, email=email)

            # Fix: Use the correct field names from your User model
            if role_type == 'admin':
                user.admin = is_checked  # Use 'admin' field, not 'is_superuser'
            elif role_type == 'staff':
                user.staff = is_checked  # Use 'staff' field, not 'is_staff'
            
            user.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
@user_passes_test(is_admin)
def add_user(request):
    """Add new user"""
    if request.method == 'POST':
        try:
            email = request.POST.get('email')
            full_name = request.POST.get('name')
            password = request.POST.get('password')
            role = request.POST.get('role', 'user')
            
            # Check if user already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, 'User with this email already exists.')
                return redirect('admin:dashboard')
            
            # Fix: Use your custom User model fields and manager
            # Determine role flags
            is_admin = (role == 'admin')
            is_staff = (role == 'staff')
            
            # Use your custom create_user method
            user = User.objects.create_user(
                email=email,
                name=full_name,  # Use 'name' field from your model
                password=password,
                is_admin=is_admin,
                is_staff=is_staff,
                is_active=True
            )
            
            messages.success(request, f'User {email} created successfully.')
            
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
    
    return redirect('admin:dashboard')