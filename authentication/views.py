import threading
from urllib.parse import urlparse
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_POST

from events.models import Category, Event, EventBooking, EventPublishStatus, Ticket, Notification, NotificationType
from events.exports import export_events_excel, export_events_pdf
from events.emails import send_booking_cancellation_email

from .decorators import admin_required, organizer_required, role_required
from .emails import send_verification_email
from .forms import UserRegistrationForm
from .models import OrganizerApprovalStatus, User, UserRole


@login_not_required
def register(request):
    if request.user.is_authenticated:
        if request.user.is_admin:
            return redirect('admin_dashboard')
        return redirect('home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.email_verified = False
            user.save()

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            verification_path = reverse(
                'verify_email',
                kwargs={
                    'uidb64': uid,
                    'token': token,
                },
            )
            site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
            verification_url = f'{site_url}{verification_path}'

            try:
                send_verification_email(user, verification_url)
            except Exception as e:
                print(f"Failed to send verification email: {e}")

            # If the user registered as organizer (pending approval), notify all admins
            if user.is_organizer and user.organizer_status == OrganizerApprovalStatus.PENDING:
                try:
                    admin_users = User.objects.filter(role=UserRole.ADMIN, is_active=True)
                    for admin_user in admin_users:
                        Notification.objects.create(
                            recipient=admin_user,
                            title='New Organizer Request',
                            message=f'User @{user.username} has registered as an organizer and is pending approval.',
                            notification_type=NotificationType.ORGANIZER_REQUEST,
                        )
                except Exception:
                    pass

            return redirect('verification_pending')
    else:
        form = UserRegistrationForm()

    return render(
        request,
        'authentication/register.html',
        {'form': form}
    )


@login_not_required
def verification_pending(request):
    return render(request, 'authentication/verification_pending.html')


@login_not_required
def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return render(request, 'authentication/email_verification_invalid.html')

    if user.email_verified:
        return render(request, 'authentication/email_verification_success.html', {'user': user})

    if default_token_generator.check_token(user, token):
        user.email_verified = True
        user.save(update_fields=['email_verified'])
        return render(request, 'authentication/email_verification_success.html', {'user': user})

    return render(request, 'authentication/email_verification_invalid.html')


@login_not_required
def register_success(request):
    return render(request, 'authentication/register_success.html')


@login_not_required
def home(request):
    if request.user.is_authenticated:
        if request.user.is_admin:
            return redirect('admin_dashboard')
        elif request.user.is_organizer:
            return redirect('organizer_dashboard')
        elif request.user.is_attendee:
            return redirect('attendee_dashboard')

    featured_events = Event.objects.filter(date__gte=timezone.now()).order_by('date')[:5]
    return render(request, 'authentication/home.html', {'featured_events': featured_events})


@admin_required
def admin_dashboard(request):
    users = User.objects.all()
    organizers = users.filter(role=UserRole.ORGANIZER)
    attendees = users.filter(role=UserRole.ATTENDEE)
    upcoming_events = Event.objects.filter(
        date__gte=timezone.now()
    ).order_by('date')[:5]

    context = {
        'events': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'categories': Event.get_all_category_choices(),
        'search_query': search_query,
        'selected_category': selected_category,
        'max_price': max_price,
        'start_date': start_date,
        'end_date': end_date,
        'filter_query_string': filter_query_string,
        'past_events': past_events,
        'selling_fast_threshold': selling_fast_threshold,
        'featured_events': featured_events,
    }
    return render(request, 'events/event_list.html', context)

def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    user = request.user

    if not _user_can_see_unpublished_event(user, event):
        raise PermissionDenied("This event is not currently published.")

    user_has_booked = False

    if user.is_authenticated:
        user_has_booked = _user_has_booked_event(user, event)

    context = {
        'event': event,
        'can_manage': user.is_authenticated and _user_can_manage_event(user, event),
        'can_review_event': user.is_authenticated and user.is_admin,
        'can_book': (
            user.is_authenticated
            and user.role == UserRole.ATTENDEE
            and not user_has_booked
            and not event.is_sold_out
            and not event.is_expired
            and event.is_published
        ),
        'user_has_booked': user_has_booked,
        'is_past_event': event.is_expired,
    }
    return render(request, 'events/event_detail.html', context)


@role_required(UserRole.ATTENDEE)
def book_event(request, pk):
    """Keep the legacy endpoint from bypassing the ticket-capacity flow."""
    return redirect('book_ticket', pk=pk)


@attendee_required
def book_ticket(request, pk):
    """Book tickets without allowing a request to exceed event capacity."""
    event = get_object_or_404(Event, pk=pk)

    if event.is_expired:
        messages.error(request, 'Booking is not available because this event has ended.')
        return redirect('event_detail', pk=pk)

    if _user_has_booked_event(request.user, event):
        messages.info(request, 'You have already booked this event.')
        return redirect('event_detail', pk=pk)

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 0

        if quantity < 1:
            messages.error(request, 'Choose at least one ticket.')
        else:
            with transaction.atomic():
                tickets_sold = event.tickets_sold
                remaining = event.max_tickets - tickets_sold

                if quantity > remaining:
                    if remaining <= 0:
                        messages.error(request, 'This event is sold out.')
                    else:
                        messages.error(
                            request,
                            f'Only {remaining} ticket(s) remain for this event.',
                        )
                elif _user_has_booked_event(request.user, event):
                    messages.info(request, 'You have already booked this event.')
                else:
                    ticket = Ticket.objects.create(
                        event=event,
                        attendee=request.user,
                        quantity=quantity,
                    )
                    EventBooking.objects.get_or_create(
                        user=request.user,
                        event=event,
                    )
                    
                   
                    threading.Thread(
                        target=send_booking_confirmation_email,
                        args=(ticket,)
                    ).start()

                    messages.success(
                        request,
                        f'Ticket booked for "{event.title}". Confirmation email is on its way.',
                    )

                    return redirect('attendee_dashboard')

    return render(
        request,
        'authentication/user_confirm_delete.html',
        {'target_user': target},
    )


@login_not_required
def login_view(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user is None:
            messages.error(request, 'Invalid username or password')
        else:
            if not user.is_admin and not user.email_verified:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                verification_path = reverse(
                    'verify_email',
                    kwargs={
                        'uidb64': uid,
                        'token': token,
                    },
                )
                site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
                verification_url = f'{site_url}{verification_path}'

                try:
                    send_verification_email(user, verification_url)
                except Exception as e:
                    print(f"Failed to send verification email: {e}")

                messages.error(
                    request,
                    'Please verify your email address before logging in. A new verification link has been sent to your email.',
                )
                return render(request, 'authentication/login.html')

            login(request, user)
            if user.is_admin:
                return redirect('admin_dashboard')
            if user.is_organizer:
                return redirect('organizer_dashboard')
            return redirect('attendee_dashboard')

    return render(request, 'authentication/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def unauthorized(request):
    return render(request, 'authentication/unauthorized.html', status=403)


@organizer_required
def request_organizer_approval(request):
    """Allow an organizer to submit or re-submit a request to the admin for event creation approval."""
    if request.user.organizer_status != OrganizerApprovalStatus.APPROVED:
        request.user.organizer_status = OrganizerApprovalStatus.PENDING
        request.user.save(update_fields=['organizer_status'])

        try:
            admin_users = User.objects.filter(role=UserRole.ADMIN, is_active=True)
            for admin_user in admin_users:
                Notification.objects.create(
                    recipient=admin_user,
                    title='Organizer Access Request',
                    message=f'Organizer @{request.user.username} has submitted a request for event creation access.',
                    notification_type=NotificationType.ORGANIZER_REQUEST,
                )
        except Exception:
            pass

        messages.success(request, 'Your request for event creation access has been submitted to the administrator.')
    return redirect('organizer_dashboard')


@organizer_required
def organizer_dashboard(request):
    """Dashboard showing ticket sales performance, revenue, and charts for the organizer's events."""
    events = Event.objects.filter(organizer=request.user).order_by('-date')
    upcoming_events = Event.objects.filter(date__gte=timezone.now()).order_by('date')[:3]

    total_events = events.count()
    total_tickets_sold = sum(event.tickets_sold for event in events)
    total_tickets_remaining = sum(event.tickets_remaining for event in events)
    total_revenue = sum((event.revenue for event in events), Decimal('0.00'))

    # Chronological order for chart rendering (oldest to newest)
    chart_events = list(reversed(list(events)))
    chart_labels = [e.title for e in chart_events]
    chart_tickets_sold = [e.tickets_sold for e in chart_events]
    chart_tickets_remaining = [e.tickets_remaining for e in chart_events]
    chart_revenue = [float(e.revenue) for e in chart_events]

    context = {
        'upcoming_events': upcoming_events,
        'events': events,
        'total_events': total_events,
        'total_tickets_sold': total_tickets_sold,
        'total_tickets_remaining': total_tickets_remaining,
        'total_revenue': total_revenue,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_tickets_sold_json': json.dumps(chart_tickets_sold),
        'chart_tickets_remaining_json': json.dumps(chart_tickets_remaining),
        'chart_revenue_json': json.dumps(chart_revenue),
    }
    return render(request, 'authentication/organizer_dashboard.html', context)


@organizer_required
def organizer_event_list(request):
    """Show only events owned by the logged-in organizer."""
    events = Event.objects.filter(organizer=request.user).order_by('-date')

    upcoming_events = Event.objects.filter(
    date__gte=timezone.now()
    ).order_by('date')[:3]

    total_events = events.count()
    total_tickets_sold = sum(event.tickets_sold for event in events)
    total_tickets_remaining = sum(event.tickets_remaining for event in events)
    total_revenue = float(sum((event.revenue for event in events), Decimal('0.00')))

    chart_events = list(reversed(list(events)))
    chart_labels = [e.title for e in chart_events]
    chart_tickets_sold = [e.tickets_sold for e in chart_events]
    chart_tickets_remaining = [e.tickets_remaining for e in chart_events]
    chart_revenue = [float(e.revenue) for e in chart_events]

    events_data = [
        {
            'pk': e.pk,
            'title': e.title,
            'price': str(e.price),
            'tickets_sold': e.tickets_sold,
            'tickets_remaining': e.tickets_remaining,
            'max_tickets': e.max_tickets,
            'revenue': float(e.revenue),
            'is_sold_out': e.is_sold_out,
        }
        for e in events
    ]

    return JsonResponse({
        'total_events': total_events,
        'total_tickets_sold': total_tickets_sold,
        'total_tickets_remaining': total_tickets_remaining,
        'total_revenue': total_revenue,
        'chart_labels': chart_labels,
        'chart_tickets_sold': chart_tickets_sold,
        'chart_tickets_remaining': chart_tickets_remaining,
        'chart_revenue': chart_revenue,
        'events': events_data,
    })


def _apply_export_filters(events, request):
    """Apply search and category query-string filters to an events queryset."""
    search_query = request.GET.get('search', '').strip()
    category_param = request.GET.get('category', '').strip()

    if search_query:
        from django.db.models import Q
        events = events.filter(
            Q(title__icontains=search_query)
            | Q(organizer__username__icontains=search_query)
            | Q(location__icontains=search_query)
        )

    if category_param:
        category_names = [c.strip() for c in category_param.split(',') if c.strip()]
        if category_names:
            events = events.filter(categories__name__in=category_names).distinct()

    return events


@login_required
def organizer_export_excel(request):
    """Download Excel (.xlsx) export of event analytics for organizers or admins."""
    if not (request.user.is_organizer or request.user.is_admin):
        return redirect('unauthorized')

    if request.user.is_admin:
        event = get_object_or_404(Event, pk=pk)
    else:
        events = Event.objects.filter(organizer=request.user).order_by('-date')

    events = _apply_export_filters(events, request)

    return export_events_excel(events, user=request.user)


@login_required
def organizer_export_pdf(request):
    """Download styled PDF analytics report with revenue metrics, charts, and key stats."""
    if not (request.user.is_organizer or request.user.is_admin):
        return redirect('unauthorized')

    if request.user.is_admin:
        organizer_id = request.GET.get('organizer')
        if organizer_id:
            events = Event.objects.filter(organizer_id=organizer_id).order_by('-date')
        else:
            events = Event.objects.all().order_by('-date')
    else:
        events = Event.objects.filter(organizer=request.user).order_by('-date')

    events = _apply_export_filters(events, request)

    total_events = events.count()
    total_tickets_sold = sum(event.tickets_sold for event in events)
    total_tickets_remaining = sum(event.tickets_remaining for event in events)
    total_revenue = sum((event.revenue for event in events), Decimal('0.00'))

    return export_events_pdf(
        events=events,
        total_events=total_events,
        total_tickets_sold=total_tickets_sold,
        total_tickets_remaining=total_tickets_remaining,
        total_revenue=total_revenue,
        user=request.user,
    )


@organizer_or_admin_required
def event_delete(request, pk):
    """Delete an event only if it belongs to the logged-in organizer."""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully.')
        if request.user.is_admin:
            return redirect('admin_dashboard')
        return redirect('my_events') # التعديل هنا ليعود لصفحة My Events بعد الحذف

    return render(
        request,
        'events/event_confirm_delete.html',
        {'event': event},
    )

@admin_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'events/category_list.html', {'categories': categories})


@admin_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                'Category created successfully.',
            )

            return redirect('admin_dashboard')

    else:
        form = CategoryForm()

    return render(
        request,
        'events/category_form.html',
        {
            'form': form,
            'page_title': 'Create Category',
            'submit_label': 'Save Category',
        },
    )


@admin_required
@require_POST
def organizer_request_approve(request, pk):
    organizer = get_object_or_404(
        User,
        pk=pk,
        role=UserRole.ORGANIZER,
    )
    organizer.organizer_status = OrganizerApprovalStatus.APPROVED
    organizer.save(update_fields=['organizer_status'])

    try:
        Notification.objects.create(
            recipient=organizer,
            title="Organizer Access Approved 🎉",
            message="Congratulations! Your organizer access has been approved by the administrator. You can now create and publish events.",
            notification_type=NotificationType.ORGANIZER_APPROVAL,
        )
    except Exception as notif_err:
        print(f"Failed to create approval notification: {notif_err}")

    messages.success(
        request,
        'events/category_form.html',
        {
            'form': form,
            'category': category,
            'page_title': 'Edit Category',
            'submit_label': 'Update Category',
        },
    )


@admin_required
@require_POST
def organizer_request_deny(request, pk):
    organizer = get_object_or_404(
        User,
        pk=pk,
        role=UserRole.ORGANIZER,
    )
    organizer.organizer_status = OrganizerApprovalStatus.DENIED
    organizer.save(update_fields=['organizer_status'])

    try:
        Notification.objects.create(
            recipient=organizer,
            title="Organizer Access Update",
            message="Your request for organizer access has been declined or revoked by the administrator.",
            notification_type=NotificationType.ORGANIZER_DENIAL,
        )
    except Exception as notif_err:
        print(f"Failed to create denial notification: {notif_err}")

    messages.success(
        request,
        "events/my_events.html",
        {
            "events": events,
        },
    )


@admin_required
def ticket_edit(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if request.method == "POST":
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, "Ticket updated successfully.")
            return redirect("admin_booking_list")
    else:
        form = TicketForm(instance=ticket)

    return render(
        request,
        "events/ticket_form.html",
        {
            "form": form,
            "ticket": ticket,
            "page_title": "Edit Ticket",
            "submit_label": "Update Ticket",
        },
    )


@admin_required
@require_POST
def event_request_approve(request, pk):
    event = get_object_or_404(Event, pk=pk)
    event.publish_status = EventPublishStatus.APPROVED
    event.save(update_fields=['publish_status'])

    try:
        Notification.objects.create(
            recipient=event.organizer,
            title='Event Approved 🎉',
            message=f'Your event "{event.title}" has been approved by an administrator and is now live!',
            event=event,
            notification_type=NotificationType.EVENT_APPROVAL,
        )
    except Exception as notif_err:
        print(f"Failed to create event approval notification: {notif_err}")

    messages.success(
        request,
        "events/ticket_confirm_delete.html",
        {
            "ticket": ticket,
        },
    )


@admin_required
@require_POST
def event_request_deny(request, pk):
    event = get_object_or_404(Event, pk=pk)
    event.publish_status = EventPublishStatus.DENIED
    event.save(update_fields=['publish_status'])

    try:
        Notification.objects.create(
            recipient=event.organizer,
            title='Event Denied',
            message=f'Your event "{event.title}" was not approved by an administrator.',
            event=event,
            notification_type=NotificationType.EVENT_DENIAL,
        )
    except Exception as notif_err:
        print(f"Failed to create event denial notification: {notif_err}")

    messages.success(
        request,
        "events/booking_form.html",
        {
            "form": form,
            "booking": booking,
            "page_title": "Edit Booking",
            "submit_label": "Update Booking",
        },
    )


@admin_required
def booking_delete(request, pk):
    booking = get_object_or_404(EventBooking, pk=pk)

    if request.method == "POST":
        Ticket.objects.filter(attendee=booking.user, event=booking.event).delete()
        booking.delete()
        messages.success(request, "Booking deleted successfully.")
        return redirect("admin_booking_list")

    return render(
        request,
        "events/booking_confirm_delete.html",
        {
            "booking": booking,
        },
    )

@admin_required
def admin_booking_list(request):
    for ticket in Ticket.objects.select_related('attendee', 'event').all():
        EventBooking.objects.get_or_create(
            user=ticket.attendee,
            event=ticket.event,
            defaults={'booked_at': ticket.booked_at}
        )
    bookings = EventBooking.objects.select_related('user', 'event').order_by('-booked_at')
    return render(request, 'events/admin_booking_list.html', {'bookings': bookings})

create_event = event_create
edit_event = event_edit
delete_event = event_delete


# =========================================================
# Real-Time Notification APIs
# =========================================================

import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def user_notifications_api(request):
    """API endpoint to fetch the top 5 recent notifications for the logged-in user."""
    notifications = Notification.objects.filter(recipient=request.user)
    unread_count = notifications.filter(is_read=False).count()

    notifications_data = [
        {
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M')
        }
        for n in notifications[:5]
    ]
    return JsonResponse({
        'unread_count': unread_count,
        'notifications': notifications_data
    })


@login_required
def mark_notification_as_read(request, pk):
    """API endpoint to mark a specific notification as read."""
    if request.method == 'POST':
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=400)


@login_required
def save_fcm_token(request):
    """Save the user's FCM token for push notifications."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('token')
            if token:
                request.user.fcm_token = token
                request.user.save()
                return JsonResponse({'status': 'success', 'message': 'Token saved successfully'})
            return JsonResponse({'status': 'error', 'message': 'No token provided'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
