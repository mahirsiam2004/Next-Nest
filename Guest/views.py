from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.template import loader
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.views import LogoutView
from django.db.models import Q
from user.models import Room, House, Contact, User
import re
from django.contrib.auth.decorators import user_passes_test
from django.utils.http import url_has_allowed_host_and_scheme


def index(request):
    template = loader.get_template('index.html')
    context = {}

    rooms = Room.objects.all()
    if rooms.exists():
        n = rooms.count()
        nslide = n // 3 + (n % 3 > 0)
        context['room'] = [rooms, range(1, nslide + 1), n]

    houses = House.objects.all()
    if houses.exists():
        n = houses.count()
        nslide = n // 3 + (n % 3 > 0)
        context['house'] = [houses, range(1, nslide + 1), n]

    return HttpResponse(template.render(context, request))


def home(request):
    # Get all unique locations and cities for suggestions
    room_locations = Room.objects.values_list('location', 'city').distinct()
    house_locations = House.objects.values_list('location', 'city').distinct()
    
    all_locations = set()
    for location, city in list(room_locations) + list(house_locations):
        if location:
            all_locations.add(location.title())
        if city:
            all_locations.add(city.title())
    
    context = {
        'result': '',
        'msg': 'Search your query',
        'locations': sorted(list(all_locations))
    }
    return render(request, 'home.html', context)


def extract_numeric_value(text):
    """Extract numeric value from text like '1200 sq ft' or '2 BHK'"""
    if not text:
        return 0
    
    # Remove common words and extract numbers
    import re
    numbers = re.findall(r'\d+', str(text))
    if numbers:
        return int(numbers[0])
    return 0


def search(request):
    template = loader.get_template('home.html')
    context = {}
    
    if request.method == 'GET':
        typ = request.GET.get('type', 'House')
        q = request.GET.get('q', '').strip()
        min_price = request.GET.get('min_price', '')
        max_price = request.GET.get('max_price', '')
        bedrooms = request.GET.get('bedrooms', '')
        
        # New range filters
        min_area = request.GET.get('min_area', '')  # For houses
        max_area = request.GET.get('max_area', '')  # For houses
        min_dimension = request.GET.get('min_dimension', '')  # For apartments
        max_dimension = request.GET.get('max_dimension', '')  # For apartments
        
        sort_by = request.GET.get('sort_by', 'cost')
        sort_order = request.GET.get('sort_order', 'asc')
        
        # Update context with search parameters
        context.update({
            'type': typ, 
            'q': q,
            'min_price': min_price,
            'max_price': max_price,
            'bedrooms': bedrooms,
            'min_area': min_area,
            'max_area': max_area,
            'min_dimension': min_dimension,
            'max_dimension': max_dimension,
            'sort_by': sort_by,
            'sort_order': sort_order
        })

        results = []
        if typ == 'House':
            results = House.objects.all()
        elif typ == 'Apartment':
            results = Room.objects.all()

        # Apply search filters - FIXED SEARCH LOGIC
        if q:
            # Option 1: Exact phrase matching (most precise)
            search_filter = (
                Q(location__icontains=q) |
                Q(city__icontains=q) |
                Q(desc__icontains=q)
            )
            results = results.filter(search_filter)
            
            # If no results found with exact phrase, try individual word matching
            if not results.exists():
                search_filter = Q()
                search_terms = q.lower().split()
                
                # Use AND logic - all terms must be found somewhere in the record
                for term in search_terms:
                    if len(term) > 2:  # Only search for words longer than 2 characters
                        term_filter = (
                            Q(location__icontains=term) |
                            Q(city__icontains=term) |
                            Q(desc__icontains=term)
                        )
                        if not search_filter:
                            search_filter = term_filter
                        else:
                            search_filter &= term_filter  # AND operation
                
                # Reset results and apply the new filter
                if typ == 'House':
                    results = House.objects.all()
                else:
                    results = Room.objects.all()
                
                if search_filter:
                    results = results.filter(search_filter)

        # Apply price filters
        if min_price:
            try:
                results = results.filter(cost__gte=int(min_price))
            except ValueError:
                pass
        
        if max_price:
            try:
                results = results.filter(cost__lte=int(max_price))
            except ValueError:
                pass

        # Apply bedroom filter
        if bedrooms:
            try:
                results = results.filter(bedrooms=int(bedrooms))
            except ValueError:
                pass

        # Apply area range filter for houses
        if typ == 'House':
            if min_area:
                try:
                    min_area_val = int(min_area)
                    # Filter by extracting numeric values from area field
                    filtered_ids = []
                    for house in results:
                        area_numeric = extract_numeric_value(house.area)
                        if area_numeric >= min_area_val:
                            filtered_ids.append(house.house_id)
                    results = results.filter(house_id__in=filtered_ids)
                except ValueError:
                    pass
            
            if max_area:
                try:
                    max_area_val = int(max_area)
                    # Filter by extracting numeric values from area field
                    filtered_ids = []
                    for house in results:
                        area_numeric = extract_numeric_value(house.area)
                        if area_numeric <= max_area_val:
                            filtered_ids.append(house.house_id)
                    results = results.filter(house_id__in=filtered_ids)
                except ValueError:
                    pass

        # Apply dimension range filter for apartments
        if typ == 'Apartment':
            if min_dimension:
                try:
                    min_dim_val = int(min_dimension)
                    # Filter by extracting numeric values from dimension field
                    filtered_ids = []
                    for room in results:
                        dim_numeric = extract_numeric_value(room.dimention)
                        if dim_numeric >= min_dim_val:
                            filtered_ids.append(room.room_id)
                    results = results.filter(room_id__in=filtered_ids)
                except ValueError:
                    pass
            
            if max_dimension:
                try:
                    max_dim_val = int(max_dimension)
                    # Filter by extracting numeric values from dimension field
                    filtered_ids = []
                    for room in results:
                        dim_numeric = extract_numeric_value(room.dimention)
                        if dim_numeric <= max_dim_val:
                            filtered_ids.append(room.room_id)
                    results = results.filter(room_id__in=filtered_ids)
                except ValueError:
                    pass

        # Apply sorting
        if sort_by == 'cost':
            if sort_order == 'desc':
                results = results.order_by('-cost')
            else:
                results = results.order_by('cost')
        elif sort_by == 'bedrooms':
            if sort_order == 'desc':
                results = results.order_by('-bedrooms')
            else:
                results = results.order_by('bedrooms')
        elif sort_by == 'area' and typ == 'House':
            # Custom sorting by numeric area value
            results_list = list(results)
            results_list.sort(
                key=lambda x: extract_numeric_value(x.area), 
                reverse=(sort_order == 'desc')
            )
            # Convert back to queryset-like structure for template compatibility
            results = results.filter(house_id__in=[h.house_id for h in results_list])
            if sort_order == 'desc':
                results = results.order_by('-house_id')
            else:
                results = results.order_by('house_id')
        elif sort_by == 'dimension' and typ == 'Apartment':
            # Custom sorting by numeric dimension value
            results_list = list(results)
            results_list.sort(
                key=lambda x: extract_numeric_value(x.dimention), 
                reverse=(sort_order == 'desc')
            )
            # Convert back to queryset-like structure for template compatibility
            results = results.filter(room_id__in=[r.room_id for r in results_list])
            if sort_order == 'desc':
                results = results.order_by('-room_id')
            else:
                results = results.order_by('room_id')
        elif sort_by == 'newest':
            if typ == 'House':
                results = results.order_by('-house_id')
            else:
                results = results.order_by('-room_id')

        # Get unique values for filter dropdowns
        all_results = House.objects.all() if typ == 'House' else Room.objects.all()
        
        price_ranges = [
            {'min': 0, 'max': 500, 'label': 'Under $500'},
            {'min': 500, 'max': 1000, 'label': '$500 - $1,000'},
            {'min': 1000, 'max': 2000, 'label': '$1,000 - $2,000'},
            {'min': 2000, 'max': 5000, 'label': '$2,000 - $5,000'},
            {'min': 5000, 'max': 999999, 'label': 'Above $5,000'},
        ]
        
        bedroom_options = sorted(set(all_results.values_list('bedrooms', flat=True).distinct()))
        
        # Get area/dimension ranges for houses or apartments
        if typ == 'House':
            # Generate area ranges based on actual data
            area_ranges = [
                {'min': 0, 'max': 500, 'label': 'Under 500 sq ft'},
                {'min': 500, 'max': 1000, 'label': '500 - 1,000 sq ft'},
                {'min': 1000, 'max': 1500, 'label': '1,000 - 1,500 sq ft'},
                {'min': 1500, 'max': 2000, 'label': '1,500 - 2,000 sq ft'},
                {'min': 2000, 'max': 3000, 'label': '2,000 - 3,000 sq ft'},
                {'min': 3000, 'max': 999999, 'label': 'Above 3,000 sq ft'},
            ]
            context['area_ranges'] = area_ranges
        else:
            # Generate dimension ranges for apartments (assuming BHK format)
            dimension_ranges = [
                {'min': 1, 'max': 1, 'label': '1 BHK'},
                {'min': 2, 'max': 2, 'label': '2 BHK'},
                {'min': 3, 'max': 3, 'label': '3 BHK'},
                {'min': 4, 'max': 4, 'label': '4 BHK'},
                {'min': 5, 'max': 999, 'label': '5+ BHK'},
            ]
            context['dimension_ranges'] = dimension_ranges
        
        context.update({
            'price_ranges': price_ranges,
            'bedroom_options': bedroom_options,
        })

        if not results.exists():
            messages.info(request, f"No {typ.lower()}s found matching your criteria. Try adjusting your filters.")

        # Pagination (simple implementation)
        results_count = results.count()
        page_size = 12
        page = request.GET.get('page', 1)
        try:
            page = int(page)
        except ValueError:
            page = 1
        
        start = (page - 1) * page_size
        end = start + page_size
        paginated_results = results[start:end]
        
        total_pages = (results_count + page_size - 1) // page_size
        
        context['result'] = [paginated_results, total_pages, results_count, page]
        
        # Get all unique locations for search suggestions
        room_locations = Room.objects.values_list('location', 'city').distinct()
        house_locations = House.objects.values_list('location', 'city').distinct()
        
        all_locations = set()
        for location, city in list(room_locations) + list(house_locations):
            if location:
                all_locations.add(location.title())
            if city:
                all_locations.add(city.title())
        
        context['locations'] = sorted(list(all_locations))

    return HttpResponse(template.render(context, request))


def about(request):
    return render(request, 'about.html', {
        'room': Room.objects.all(),
        'house': House.objects.all(),
    })


def contact(request):
    if request.method == 'POST':
        subject = request.POST['subject']
        email = request.POST['email']
        body = request.POST['body']
        if not re.match(r'^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$', email):
            return render(request, 'contact.html', {'msg': 'Invalid email'})
        Contact.objects.create(subject=subject, email=email, body=body)
        return render(request, 'contact.html', {'msg': 'Message sent to admin.'})
    return render(request, 'contact.html', {'msg': ''})


def descr(request):
    if request.method == 'GET':
        prop_id = request.GET.get('id')
        property_type = request.GET.get('type')  # Get the property type from the form
        
        if not prop_id:
            raise Http404("Property ID is required")
            
        try:
            prop_id = int(prop_id)
        except (ValueError, TypeError):
            raise Http404("Invalid property ID")
        
        # Check property type first if provided
        if property_type == 'apartment':
            try:
                room = get_object_or_404(Room, room_id=prop_id)
                context = {
                    'val': room, 
                    'type': 'Apartment', 
                    'user': room.user_email,
                    'property_id': room.room_id,
                    'verified': room.verified,
                    'date_listed': room.date,
                    # Include all relevant Room model fields
                    'dimensions': room.dimention,  # Note: keeping original field name
                    'location': room.location,
                    'city': room.city,
                    'cost': room.cost,
                    'bedrooms': room.bedrooms,
                    'kitchen': room.kitchen,
                    'floor': room.floor,
                    'balcony': room.balcany,  # Note: keeping original field name
                    'description': room.desc,
                    'image': room.img,
                }
                return render(request, 'desc.html', context)
            except Http404:
                raise Http404("Apartment not found")
                
        elif property_type == 'house':
            try:
                house = get_object_or_404(House, house_id=prop_id)
                context = {
                    'val': house, 
                    'type': 'House', 
                    'user': house.user_email,
                    'property_id': house.house_id,
                    'verified': house.verified,
                    'date_listed': house.date,
                    # Include all relevant House model fields
                    'area': house.area,
                    'location': house.location,
                    'city': house.city,
                    'cost': house.cost,
                    'bedrooms': house.bedrooms,
                    'kitchen': house.kitchen,  # This is IntegerField for houses
                    'floor': house.floor,
                    'balcony': house.balcany,  # Note: keeping original field name
                    'description': house.desc,
                    'image': house.img,
                }
                return render(request, 'desc.html', context)
            except Http404:
                raise Http404("House not found")
        
        # Fallback to original logic if no type specified (for backward compatibility)
        else:
            try:
                room = get_object_or_404(Room, room_id=prop_id)
                context = {
                    'val': room, 
                    'type': 'Apartment', 
                    'user': room.user_email,
                    'property_id': room.room_id,
                    'verified': room.verified,
                    'date_listed': room.date,
                }
                return render(request, 'desc.html', context)
            except Http404:
                try:
                    house = get_object_or_404(House, house_id=prop_id)
                    context = {
                        'val': house, 
                        'type': 'House', 
                        'user': house.user_email,
                        'property_id': house.house_id,
                        'verified': house.verified,
                        'date_listed': house.date,
                    }
                    return render(request, 'desc.html', context)
                except Http404:
                    raise Http404("Property not found")
    
    # If not GET request, redirect to home or appropriate page
    return redirect('/')  # Make sure you have appropriate URL name or use reverse

def register(request):
    if request.method == 'GET':
        return render(request, 'register.html', {'msg': ''})

    name = request.POST['name']
    email = request.POST['email']
    pas = request.POST['pass']

    if not re.match(r'^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$', email):
        return render(request, 'register.html', {'msg': 'Invalid email'})

    if User.objects.filter(email=email).exists():
        return render(request, 'register.html', {'msg': 'Email already registered'})

    user = User.objects.create(
        name=name,
        email=email,
        password=make_password(pas)  # hash password
    )

    # Authenticate and log in
    user = authenticate(request, email=email, password=pas)
    if user:
        login(request, user)
        return redirect("/profile/")
    return render(request, 'register.html', {'msg': 'Registration failed. Try again.'})






def login_view(request):
    if request.method == 'GET':
        return render(request, 'login.html')

    email = request.POST['email']
    password = request.POST['password']

    user = authenticate(request, email=email, password=password)
    if user:
        login(request, user)
        return redirect("/")
    return render(request, 'login.html', {'msg': 'Email and password did not match.'})


@login_required(login_url='/login')
def profile(request):
    # report = Contact.objects.filter(email=request.user.email)
    room = Room.objects.filter(user_email=request.user.email)
    house = House.objects.filter(user_email=request.user.email)

    context = {
        'user': request.user,
        # 'report': report,
        # 'reportno': report.count(),
        'roomno': room.count(),
        'houseno': house.count(),
        'room': [room, range(1, (room.count() // 3) + 2), room.count()] if room.exists() else [],
        'house': [house, range(1, (house.count() // 3) + 2), house.count()] if house.exists() else []
    }
    return render(request, 'profile.html', context)


@login_required(login_url='/login')
def post(request):
    if request.method == "GET":
        return render(request, 'post.html', {'user': request.user})

    try:
        Room.objects.create(
            user_email=request.user,
            dimention=request.POST['dimention'],
            location=request.POST['location'].lower(),
            city=request.POST['city'].lower(),
            floor=request.POST['floor'],
            cost=int(request.POST['cost']),
            kitchen=request.POST['kitchen'].lower(),
            balcany=request.POST['balcany'].lower(),
            bedrooms=int(request.POST['bedroom']),
            desc=request.POST['desc'].upper(),
            img=request.FILES['img']
        )
        messages.success(request, 'Apartment posted successfully.')
    except Exception as e:
        print(e)
        return HttpResponse(status=500)

    return render(request, 'post.html')


@login_required(login_url='/login')
def posth(request):
    if request.method == "GET":
        return render(request, 'posth.html', {'user': request.user})

    try:
        House.objects.create(
            user_email=request.user,
            area=request.POST['area'],
            floor=request.POST['floor'],
            location=request.POST['location'].lower(),
            city=request.POST['city'].lower(),
            cost=int(request.POST['cost']),
            kitchen=request.POST['kitchen'].lower(),
            balcany=request.POST['balcany'].lower(),
            bedrooms=int(request.POST['bedroom']),
            desc=request.POST['desc'].upper(),
            img=request.FILES['img']
        )
        messages.success(request, 'House posted successfully.')
    except Exception as e:
        print(e)
        return HttpResponse(status=500)

    return render(request, 'posth.html')


@login_required(login_url='/login')
def deleter(request):
    if request.method == 'GET':
        id = request.GET.get('id')
        Room.objects.filter(room_id=id, user_email=request.user.email).delete()
        messages.success(request, 'Apartment deleted successfully.')
    return redirect('/profile')


@login_required(login_url='/login')
def deleteh(request):
    if request.method == 'GET':
        id = request.GET.get('id')
        House.objects.filter(house_id=id, user_email=request.user.email).delete()
        messages.success(request, 'House deleted successfully.')
    return redirect('/profile')




def view_all(request, property_type):
    """
    View to display all properties of a specific type (apartment/house) with filtering and pagination
    """
    # Validate property type
    if property_type not in ['apartment', 'house']:
        raise Http404("Invalid property type")
    
    # Get the appropriate model based on property type
    if property_type == 'apartment':
        model = Room
        properties = Room.objects.all()
    else:
        model = House
        properties = House.objects.all()
    
    # Get filter parameters from GET request
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    bedrooms = request.GET.get('bedrooms', '')
    city = request.GET.get('city', '')
    sort_by = request.GET.get('sort', 'newest')
    
    # Apply price filters
    if min_price:
        try:
            properties = properties.filter(cost__gte=int(min_price))
        except ValueError:
            pass
    
    if max_price:
        try:
            properties = properties.filter(cost__lte=int(max_price))
        except ValueError:
            pass
    
    # Apply bedrooms filter
    if bedrooms:
        try:
            bedroom_count = int(bedrooms)
            if bedroom_count == 5:
                # Handle "5+ Bedrooms" case
                properties = properties.filter(bedrooms__gte=5)
            else:
                properties = properties.filter(bedrooms=bedroom_count)
        except ValueError:
            pass
    
    # Apply city filter
    if city:
        properties = properties.filter(city__iexact=city)
    
    # Apply sorting
    if sort_by == 'price_low':
        properties = properties.order_by('cost')
    elif sort_by == 'price_high':
        properties = properties.order_by('-cost')
    elif sort_by == 'bedrooms':
        properties = properties.order_by('-bedrooms', 'cost')
    else:  # newest or default
        if property_type == 'apartment':
            properties = properties.order_by('-room_id')
        else:
            properties = properties.order_by('-house_id')
    
    # Get all unique cities for filter dropdown
    if property_type == 'apartment':
        cities = Room.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city__exact='')
    else:
        cities = House.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city__exact='')
    
    # Pagination
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    paginator = Paginator(properties, 12)  # Show 12 properties per page
    page = request.GET.get('page')
    
    try:
        properties = paginator.page(page)
    except PageNotAnInteger:
        properties = paginator.page(1)
    except EmptyPage:
        properties = paginator.page(paginator.num_pages)
    
    context = {
        'properties': properties,
        'property_type': property_type,
        'cities': sorted(cities) if cities else [],
        'is_paginated': paginator.num_pages > 1,
        'page_obj': properties,
    }
    
    return render(request, 'view_all.html', context)





