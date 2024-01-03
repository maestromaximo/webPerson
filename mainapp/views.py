from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import BudgetLog, FieldEntry, Account, Budget, BudgetCategory
import json
from datetime import datetime, timedelta
from .utils import classify_transaction_simple, classify_transaction_advanced, update_budget_and_mark_entry
from django.utils.timezone import make_aware

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
            name="Default Budget",
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
            entry = FieldEntry.objects.create(
                date=datetime.strptime(data['date'], "%Y-%m-%d").date(),
                time=datetime.strptime(data['time'], "%H:%M:%S").time(),
                message=data['message'],
                money=data['amount'],
                read_status=False 
            )
            entry.save()
            return JsonResponse({'status': 'success', 'message': 'Entry saved'})
        except Exception as e:
            print(e)
            return JsonResponse({'status': 'error', 'message': 'Error processing request'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed.'})
    

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

def dashboard(request):
    context = {

    }

    return render(request, 'dashboard.html', context)

def budget(request):
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

    start_of_week = today - timedelta(days=today.weekday())
    this_week_entries = FieldEntry.objects.filter(date__gte=start_of_week, category__isnull=True, accounted_for=False)
    for entry in this_week_entries:
        update_budget_and_mark_entry(entry)

    context = {
        'budget_categories': budget_categories,
    }
    return render(request, 'budgets.html', context)

def update_budget(request):
    if request.method == 'POST':
        for category in BudgetCategory.objects.all():
            new_limit = request.POST.get(f'limit_{category.id}')
            if new_limit is not None:
                category.weekly_limit = new_limit
                category.save()
    return redirect('budget')
