from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from .models import BigCat, Vocalization
from .forms import BigCatForm, VocalizationForm

@login_required
def admin_dashboard(request):
    return render(request, 'admin/dashboard.html')

@login_required
def manage_big_cats(request):
    big_cats = BigCat.objects.all()
    return render(request, 'admin/manage_big_cats.html', {'big_cats': big_cats})

@login_required
def add_big_cat(request):
    if request.method == 'POST':
        form = BigCatForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('admin:manage_big_cats'))
    else:
        form = BigCatForm()
    return render(request, 'admin/add_big_cat.html', {'form': form})

@login_required
def edit_big_cat(request, big_cat_id):
    big_cat = get_object_or_404(BigCat, pk=big_cat_id)
    if request.method == 'POST':
        form = BigCatForm(request.POST, instance=big_cat)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('admin:manage_big_cats'))
    else:
        form = BigCatForm(instance=big_cat)
    return render(request, 'admin/edit_big_cat.html', {'form': form})

@login_required
def delete_big_cat(request, big_cat_id):
    big_cat = get_object_or_404(BigCat, pk=big_cat_id)
    big_cat.delete()
    return HttpResponseRedirect(reverse('admin:manage_big_cats'))

@login_required
def manage_vocalizations(request):
    vocalizations = Vocalization.objects.all()
    return render(request, 'admin/manage_vocalizations.html', {'vocalizations': vocalizations})

@login_required
def add_vocalization(request):
    if request.method == 'POST':
        form = VocalizationForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('admin:manage_vocalizations'))
    else:
        form = VocalizationForm()
    return render(request, 'admin/add_vocalization.html', {'form': form})

@login_required
def edit_vocalization(request, vocalization_id):
    vocalization = get_object_or_404(Vocalization, pk=vocalization_id)
    if request.method == 'POST':
        form = VocalizationForm(request.POST, instance=vocalization)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('admin:manage_vocalizations'))
    else:
        form = VocalizationForm(instance=vocalization)
    return render(request, 'admin/edit_vocalization.html', {'form': form})

@login_required
def delete_vocalization(request, vocalization_id):
    vocalization = get_object_or_404(Vocalization, pk=vocalization_id)
    vocalization.delete()
    return HttpResponseRedirect(reverse('admin:manage_vocalizations'))