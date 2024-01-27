from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import BudgetLog, FieldEntry, Account, Budget, BudgetCategory
import json
from datetime import datetime, timedelta
from .utils import classify_transaction_simple, classify_transaction_advanced, update_budget_and_mark_entry
from django.utils.timezone import make_aware
from django.db.models import Sum, Avg, Count
from random import choice
import random
from django.db.models import F
import random
from django.contrib.auth.decorators import login_required


def home(request):
    today = datetime.today().date()
    start_of_week = today - timedelta(days=today.weekday())
    
    # print(start_of_week)
    # Categorize transactions from this week
    this_week_entries = FieldEntry.objects.filter(date__gte=start_of_week, category__isnull=True)
    for entry in this_week_entries:
        entry.category = classify_transaction_simple(entry, set_misc=False)
        # print(classify_transaction_advanced(entry))
        entry.save()

    # Get the current week's Monday's date
    current_week_start = start_of_week  # Note: This is already a date object

    # Try to get the budget for the current week
    try:
        current_budget = Budget.objects.get(name="Default Budget", start_date=current_week_start)
    except Budget.DoesNotExist:
        # If not exist, create a new budget
        current_budget = Budget.objects.create(
            name="Default Budget" + str(random.randint(1, 1000)),
            start_date=current_week_start,
            end_date=current_week_start + timedelta(days=7)
        )

    # Check if the budget's start date is older than this week's start date
    if current_budget.start_date < current_week_start:
        # Reset the budget save to log

        budget_data = {}
        for category in BudgetCategory.CATEGORY_CHOICES:
            category_name = category[0]
            budget_category = current_budget.categories.get(name=category_name)
            budget_data[f'{category_name}_limit'] = budget_category.weekly_limit
            budget_data[f'{category_name}_spent'] = budget_category.amount_spent

        # Create the BudgetLog entry
        log = BudgetLog.objects.create(
            start_week=current_budget.start_date,
            end_week=current_budget.start_date + timedelta(days=7),
            **budget_data
        )


        current_budget.start_date = current_week_start
        current_budget.end_date = current_week_start + timedelta(days=7)
        current_budget.reset_weekly_budget()
        current_budget.save()

        # Reset the amounts spent in each category
        for category in current_budget.categories.all():
            category.amount_spent = 0
            category.save()

    return render(request, 'home.html')

@csrf_exempt  # Disable CSRF for this view
def purchase_made_endpoint(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            date = datetime.strptime(data['date'], "%Y-%m-%d").date()
            time = datetime.strptime(data['time'], "%H:%M:%S").time()
            message = data['message']
            money = data['amount']

            # Check if an entry with the same data already exists
            existing_entry = FieldEntry.objects.filter(
                date=date,
                time=time,
                message=message,
                money=money
            ).first()

            if existing_entry:
                # Log a message to the console
                print(f"Entry already exists for {date}")
                return JsonResponse({'status': 'error', 'message': 'Entry already exists'})

            # If no existing entry, create a new one
            entry = FieldEntry.objects.create(
                date=date,
                time=time,
                message=message,
                money=money,
                read_status=False 
            )
            entry.save()
            return JsonResponse({'status': 'success', 'message': 'Entry saved'})
        except Exception as e:
            print(e)
            return JsonResponse({'status': 'error', 'message': 'Error processing request'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed.'})
    
@login_required
def classification_menu(request):
    if request.method == 'POST':
        entries = FieldEntry.objects.filter(category__isnull=True)
        for entry in entries:
            category = classify_transaction_simple(entry)
            entry.category = category
            entry.save()


        today = datetime.today().date()
        start_of_week = today - timedelta(days=today.weekday()+7)
        
        # print(start_of_week)
        # Categorize transactions from this week
        this_week_entries = FieldEntry.objects.filter(date__gte=start_of_week, category__isnull=True)
        for entry in this_week_entries:
            entry.category = classify_transaction_advanced(entry)
            entry.save()
        this_week_entries = FieldEntry.objects.filter(date__gte=start_of_week, category__isnull=True)
        for entry in this_week_entries:
            category = classify_transaction_simple(entry)
            entry.save()
        return redirect('classification_menu')  # Redirect to avoid re-posting on refresh

    total_field_entries = FieldEntry.objects.count()
    total_categorized = FieldEntry.objects.exclude(category__isnull=True).count()
    total_uncategorized = FieldEntry.objects.filter(category__isnull=True).count()

    context = {
        'total_field_entries': total_field_entries,
        'total_categorized': total_categorized,
        'total_uncategorized': total_uncategorized
    }
    return render(request, 'classification_main.html', context)

@login_required
def dashboard(request):
    """
    Renders the dashboard page with various statistics and data.

    Args:
        request: The HTTP request object.

    Returns:
        A rendered HTML template with the dashboard data.

    Raises:
        None.
    """
    # General stats
    # total_deposits = FieldEntry.objects.filter(type='deposit').aggregate(total=Sum('money'))['total'] or 0
    
    # Weekly stats
    today = datetime.today().date()

    # If you only need the date part
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    
    total_deposits = 0
    total_withdrawals = FieldEntry.objects.filter(type='withdrawal', date__range = [start_of_week, end_of_week]).aggregate(total=Sum('money'))['total'] or 0
    current_balance = total_deposits - total_withdrawals
    
    
    weekly_entries = FieldEntry.objects.filter(date__range=[start_of_week, end_of_week])
    # Weekly stats
    weekly_expenses = float(weekly_entries.aggregate(total=Sum('money'))['total'] or 0)  # Convert to float

    # Trends
    last_week_expenses = float(FieldEntry.objects.filter(
        date__range=[start_of_week - timedelta(days=7), start_of_week - timedelta(days=1)]
    ).aggregate(total=Sum('money'))['total'] or 0)  # Convert to float

    weekly_trend = ((weekly_expenses - last_week_expenses) / last_week_expenses * 100) if last_week_expenses else 0

    # Budget stats
    # Note: Ensure that your Budget model logic to reset weekly limits is properly implemented
    budget = Budget.objects.first()  # Assuming one main budget
    categories = budget.categories.all() if budget else []
    
    # Prepare data for graph
    # Here you can prepare data for a JavaScript chart library like Chart.js
    # Prepare data for graph
    graph_data = {
        'labels': [cat.name for cat in categories],
        'data': [float(cat.amount_spent) for cat in categories],  # Convert to float
        'limits': [float(cat.weekly_limit) for cat in categories],  # Convert to float
    }


    # At a glance info, such as largest expense, most common category, etc.
    # You would need to write custom queries for these, this is just an example
    largest_expense = weekly_entries.order_by('-money').first()
    most_common_category = weekly_entries.values('category').annotate(total=Count('category')).order_by('-total').first()

    context = {
        'total_deposits': float(total_deposits),
        'total_withdrawals': float(total_withdrawals),
        'current_balance': float(current_balance),
        'weekly_expenses': weekly_expenses,
        'weekly_trend': float(weekly_trend),
        'graph_data': graph_data,
        'budget_categories': categories,
        'largest_expense': largest_expense,
        'most_common_category': most_common_category,
    }
    return render(request, 'dashboard.html', context)

@login_required
def budget(request):
    """
    View function that handles the budget page.

    This function ensures the existence of default categories and a default budget.
    It categorizes transactions that are not yet categorized and transactions from the current week.
    It also handles overspending by redistributing the excess amount to eligible categories.
    Finally, it calculates the percentage of budget spent for each category and assigns a color to the category bar.

    Parameters:
    - request: The HTTP request object.

    Returns:
    - A rendered HTML template with the budget categories and their corresponding information.
    """
    # Ensure default categories exist
    default_categories = []
    for choice in BudgetCategory.CATEGORY_CHOICES:
        category, created = BudgetCategory.objects.get_or_create(name=choice[0])
        default_categories.append(category)

    # Ensure a default budget exists
    default_budget, created = Budget.objects.get_or_create(name="Default Budget")

    # If the budget was just created, or if it's missing any categories, add them
    existing_category_names = set(default_budget.categories.values_list('name', flat=True))
    missing_categories = [cat for cat in default_categories if cat.name not in existing_category_names]

    if created or missing_categories:
        default_budget.categories.add(*missing_categories)
        default_budget.save()

    budget_categories = default_budget.categories.all()

    # Ensure the existence of the "Overspent" category
    overspent_category, created = BudgetCategory.objects.get_or_create(
        name='overspent',
        defaults={'weekly_limit': 150}
    )
    if created:
        default_budget.categories.add(overspent_category)
        default_budget.save()

    # Categorize transactions that are not yet categorized
    entries = FieldEntry.objects.filter(category__isnull=True)
    for entry in entries:
        category = classify_transaction_simple(entry)
        entry.category = category
        entry.save()

    today = datetime.today().date()
    start_of_week = today - timedelta(days=today.weekday()+7)

    # Categorize transactions from this week
    this_week_entries = FieldEntry.objects.filter(date__gte=start_of_week, category__isnull=True)
    for entry in this_week_entries:
        entry.category = classify_transaction_advanced(entry)
        entry.save()
    this_week_entries = FieldEntry.objects.filter(date__gte=start_of_week, category__isnull=True)
    for entry in this_week_entries:
        category = classify_transaction_simple(entry)
        entry.save()

    start_of_week = today - timedelta(days=today.weekday())
    print('THE START HERE:', start_of_week)
    this_week_entries = FieldEntry.objects.filter(date__gte=start_of_week, category__isnull=False, accounted_for=False)
    for entry in this_week_entries:
        update_budget_and_mark_entry(entry)

    budget_categories = default_budget.categories.all()
    overspent_categories = budget_categories.filter(amount_spent__gt=F('weekly_limit'))
    eligible_categories = budget_categories.filter(amount_spent__lt=F('weekly_limit'))

    for category in overspent_categories:
        overspent_amount = category.amount_spent - category.weekly_limit
        category.amount_spent = category.weekly_limit  # Reset to the limit

        while overspent_amount > 0:
            if eligible_categories.exists():
                # Choose a random eligible category for redistribution
                eligible_categories_list = list(eligible_categories)
                recipient_category = random.choice(eligible_categories_list)

                available_space = recipient_category.weekly_limit - recipient_category.amount_spent
                redistribution_amount = min(overspent_amount, available_space)

                recipient_category.amount_spent += redistribution_amount
                overspent_amount -= redistribution_amount

                # Update the eligible categories if the recipient is now full
                if recipient_category.amount_spent >= recipient_category.weekly_limit:
                    eligible_categories = eligible_categories.exclude(id=recipient_category.id)

                recipient_category.save()
            else:
                # All categories are full, allocate to "Overspent"
                overspent_category.amount_spent += overspent_amount
                overspent_amount = 0
                overspent_category.save()

        category.save()

    for category in budget_categories:
        percent = (category.amount_spent / category.weekly_limit * 100) if category.weekly_limit else 0
        if percent <= 50:
            category.bar_color = 'bg-blue-600'
        elif percent <= 75:
            category.bar_color = 'bg-orange-500'
        else:
            category.bar_color = 'bg-red-600'

    context = {
        'budget_categories': budget_categories,
    }
    return render(request, 'budgets.html', context)


@login_required
def update_budget(request):
    if request.method == 'POST':
        for category in BudgetCategory.objects.all():
            new_limit = request.POST.get(f'limit_{category.id}')
            if new_limit is not None:
                category.weekly_limit = new_limit
                category.save()
    return redirect('budget')
