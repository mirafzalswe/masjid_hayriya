"""
HTTP views — kept thin: parse request, delegate to forms/queries, render.

Sections:
  • Auth         — login / logout
  • Dashboard    — overview metrics
  • Murojaatlar  — CRUD on requests for help
  • Shaxslar     — list of beneficiaries
  • Users        — admin-only operator management
"""
from __future__ import annotations

from datetime import date
from typing import Any

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    LoginForm, MurojaatForm, ShaxsForm,
    UserCreateForm, UserEditForm, YordamBerForm, YordamForm,
)
from .models import Holat, Murojaat, MuhtojlikTuri, Priority, Shaxs, Yordam, YordamTuri
from .permissions import (
    admin_required, can_edit, can_edit_required, is_admin, role_of,
)


PAGE_SIZE = 25
DASHBOARD_CACHE_TTL = 60  # seconds — short, dashboard refresh after edits is OK
DASHBOARD_RECENT_LIMIT = 8


def _shared_context(request) -> dict[str, Any]:
    return {
        'user_role': role_of(request.user),
        'can_edit':  can_edit(request.user),
        'is_admin':  is_admin(request.user),
    }


# ─── Auth ──────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        next_url = request.GET.get('next') or 'dashboard'
        return redirect(next_url)
    return render(request, 'auth/login.html', {
        'form': form,
    })


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


# ─── Dashboard ─────────────────────────────────────────────────────────────────

def _month_window(year: int, month: int) -> tuple[date, date]:
    """Return [start, end_exclusive) for a calendar month."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def _dashboard_metrics() -> dict[str, Any]:
    cached = cache.get('dashboard:metrics')
    if cached:
        return cached

    today = date.today()
    month_start, _ = _month_window(today.year, today.month)

    base = Murojaat.objects.all()

    # Headline counters in a single trip per status — tiny rows so it's cheap.
    by_holat = dict(base.values_list('holat').annotate(c=Count('id')))
    yangi          = by_holat.get(Holat.YANGI, 0)
    yordam_berildi = by_holat.get(Holat.YORDAM, 0)

    jami       = sum(by_holat.values())
    bu_oy      = base.filter(murojaat_sanasi__gte=month_start).count()
    favqulodda = base.filter(priority=Priority.YUQORI, holat=Holat.YANGI).count()
    yordam_summa = (
        base.filter(holat=Holat.YORDAM, yordam_miqdori__isnull=False)
            .aggregate(s=Sum('yordam_miqdori'))['s'] or 0
    )

    # 6-month bar chart with proper calendar months.
    oylik_stat = []
    y, m = today.year, today.month
    months_back = []
    for _ in range(6):
        months_back.append((y, m))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    for (yy, mm) in reversed(months_back):
        start, end = _month_window(yy, mm)
        cnt = base.filter(murojaat_sanasi__gte=start, murojaat_sanasi__lt=end).count()
        oylik_stat.append({'oy': start.strftime('%b %Y'), 'son': cnt})

    tur_stat = list(
        base.values('muhtojlik_turi')
            .annotate(son=Count('id'))
            .order_by('-son')[:5]
    )
    # Resolve display labels — values() loses get_FOO_display().
    tur_label = dict(MuhtojlikTuri.choices)
    for row in tur_stat:
        row['label'] = tur_label.get(row['muhtojlik_turi'], row['muhtojlik_turi'])

    metrics = {
        'jami': jami,
        'yangi': yangi,
        'bu_oy': bu_oy,
        'yordam_berildi': yordam_berildi,
        'favqulodda': favqulodda,
        'yordam_summa': yordam_summa,
        'oylik_stat': oylik_stat,
        'tur_stat': tur_stat,
    }
    cache.set('dashboard:metrics', metrics, DASHBOARD_CACHE_TTL)
    return metrics


@login_required
def dashboard(request):
    metrics = _dashboard_metrics()
    recent = (
        Murojaat.objects
        .select_related('shaxs', 'mas_ul_hodim')
        .order_by('priority', '-yaratilgan')[:DASHBOARD_RECENT_LIMIT]
    )
    return render(request, 'dashboard.html', {
        **metrics,
        'songi_murojaatlar': recent,
        **_shared_context(request),
    })


# ─── Murojaatlar — list / detail / create / edit / delete ──────────────────────

def _filtered_murojaatlar(request) -> tuple[Any, dict[str, str]]:
    qs = (
        Murojaat.objects
        .select_related('shaxs', 'mas_ul_hodim')
        .order_by('priority', '-murojaat_sanasi')
    )
    filters = {
        'holat':    request.GET.get('holat', '').strip(),
        'priority': request.GET.get('priority', '').strip(),
        'tur':      request.GET.get('tur', '').strip(),
        'oy':       request.GET.get('oy', '').strip(),
        'q':        request.GET.get('q', '').strip(),
    }

    if filters['holat']:
        qs = qs.filter(holat=filters['holat'])
    if filters['priority'].isdigit():
        qs = qs.filter(priority=int(filters['priority']))
    if filters['tur']:
        qs = qs.filter(muhtojlik_turi=filters['tur'])

    oy = filters['oy']
    if len(oy) == 7 and oy[4] == '-' and oy[:4].isdigit() and oy[5:].isdigit():
        try:
            year, month = int(oy[:4]), int(oy[5:])
            start, end = _month_window(year, month)
            qs = qs.filter(murojaat_sanasi__gte=start, murojaat_sanasi__lt=end)
        except ValueError:
            pass  # malformed input — silently ignore the filter

    if filters['q']:
        qs = qs.filter(
            Q(shaxs__fio__icontains=filters['q'])
            | Q(shaxs__telefon__icontains=filters['q'])
            | Q(mazmun__icontains=filters['q'])
        )

    return qs, filters


@login_required
def murojaat_list(request):
    qs, filters = _filtered_murojaatlar(request)
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'murojaatlar/list.html', {
        'murojaatlar':     page_obj.object_list,
        'page_obj':        page_obj,
        'paginator':       paginator,
        'oylar':           Murojaat.objects.dates('murojaat_sanasi', 'month', order='DESC'),
        'holat_choices':   Holat.choices,
        'priority_choices': Priority.choices,
        'tur_choices':     MuhtojlikTuri.choices,
        'filters':         filters,
        'total':           paginator.count,
        **_shared_context(request),
    })


@login_required
def murojaat_detail(request, pk):
    murojaat = get_object_or_404(
        Murojaat.objects.select_related('shaxs', 'mas_ul_hodim'),
        pk=pk,
    )
    # Shu shaxsga berilgan barcha yordamlar (bu murojaatga bog'lanmagani ham).
    # Bog'liqlik IDsi bo'yicha shablon "Shu murojaat" badge'ini chiqaradi.
    yordamlar = (
        murojaat.shaxs.yordamlar
        .select_related('qabul_qilgan', 'murojaat')
        .order_by('-sana', '-yaratilgan')
    )
    pul_summa = yordamlar.filter(turi=YordamTuri.PUL).aggregate(s=Sum('miqdor'))['s'] or 0

    return render(request, 'murojaatlar/detail.html', {
        'murojaat':    murojaat,
        'yordamlar':   yordamlar,
        'yordam_soni': yordamlar.count(),
        'pul_summa':   pul_summa,
        **_shared_context(request),
    })


@can_edit_required
def murojaat_create(request):
    """Two-mode form: pick an existing Shaxs OR create one inline.

    Both modes use Django Forms (not request.POST.get) so validation rules
    live in one place and errors round-trip back to the user.
    """
    mode = request.POST.get('mode') or request.GET.get('mode') or 'yangi'
    shaxs_form = ShaxsForm(prefix='shaxs')
    murojaat_form = MurojaatForm(prefix='mur')

    if request.method == 'POST':
        if mode == 'yangi':
            shaxs_form = ShaxsForm(request.POST, prefix='shaxs')
            murojaat_form = MurojaatForm(request.POST, prefix='mur')
            # We don't want the FK field to be required here — we'll attach
            # the freshly-saved Shaxs ourselves before saving.
            murojaat_form.fields['shaxs'].required = False

            if shaxs_form.is_valid() and murojaat_form.is_valid():
                with transaction.atomic():
                    canonical_phone = shaxs_form.cleaned_data['telefon']
                    shaxs, _ = Shaxs.objects.get_or_create(
                        telefon=canonical_phone,
                        defaults={
                            'fio':                shaxs_form.cleaned_data['fio'],
                            'manzil':             shaxs_form.cleaned_data.get('manzil', ''),
                            'qoshimcha_ma_lumot': shaxs_form.cleaned_data.get('qoshimcha_ma_lumot', ''),
                        },
                    )
                    murojaat = murojaat_form.save(commit=False)
                    murojaat.shaxs = shaxs
                    murojaat.save()
                cache.delete('dashboard:metrics')
                messages.success(request, f"✅ {shaxs.fio} ning murojaaati saqlandi.")
                return redirect('murojaat_detail', pk=murojaat.pk)

        elif mode == 'mavjud':
            murojaat_form = MurojaatForm(request.POST, prefix='mur')
            if murojaat_form.is_valid():
                murojaat = murojaat_form.save()
                cache.delete('dashboard:metrics')
                messages.success(request, "✅ Murojaat saqlandi.")
                return redirect('murojaat_detail', pk=murojaat.pk)

    return render(request, 'murojaatlar/create.html', {
        'mode': mode,
        'shaxs_form': shaxs_form,
        'murojaat_form': murojaat_form,
        'tur_choices': MuhtojlikTuri.choices,
        'priority_choices': Priority.choices,
        'shaxslar':  Shaxs.objects.order_by('fio').only('id', 'fio', 'telefon'),
        'today':     date.today().isoformat(),
        **_shared_context(request),
    })


@can_edit_required
def murojaat_edit(request, pk):
    murojaat = get_object_or_404(Murojaat, pk=pk)
    form = YordamBerForm(request.POST or None, instance=murojaat)
    if request.method == 'POST' and form.is_valid():
        form.save()
        cache.delete('dashboard:metrics')
        messages.success(request, "✅ Murojaat yangilandi.")
        return redirect('murojaat_detail', pk=pk)
    return render(request, 'murojaatlar/edit.html', {
        'form': form,
        'murojaat': murojaat,
        **_shared_context(request),
    })


@admin_required
def murojaat_delete(request, pk):
    murojaat = get_object_or_404(Murojaat, pk=pk)
    if request.method == 'POST':
        nom = murojaat.shaxs.fio
        murojaat.delete()
        cache.delete('dashboard:metrics')
        messages.success(request, f"🗑 '{nom}' murojaaati o'chirildi.")
        return redirect('murojaat_list')
    return render(request, 'murojaatlar/delete_confirm.html', {
        'murojaat': murojaat,
        **_shared_context(request),
    })


# ─── Shaxslar ──────────────────────────────────────────────────────────────────

@login_required
def shaxslar_list(request):
    q = request.GET.get('q', '').strip()
    qs = (
        Shaxs.objects
        .annotate(murojaatlar_count=Count('murojaatlar'))
        .order_by('fio')
    )
    if q:
        qs = qs.filter(Q(fio__icontains=q) | Q(telefon__icontains=q))

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'shaxslar/list.html', {
        'shaxslar':  page_obj.object_list,
        'page_obj':  page_obj,
        'paginator': paginator,
        'q':         q,
        'total':     paginator.count,
        **_shared_context(request),
    })


@login_required
def shaxs_detail(request, pk):
    shaxs = get_object_or_404(Shaxs, pk=pk)

    murojaatlar = (
        shaxs.murojaatlar
        .order_by('-murojaat_sanasi', '-yaratilgan')
    )
    yordamlar = (
        shaxs.yordamlar
        .select_related('qabul_qilgan', 'murojaat')
        .order_by('-sana', '-yaratilgan')
    )
    pul_summa = yordamlar.filter(turi=YordamTuri.PUL).aggregate(s=Sum('miqdor'))['s'] or 0

    return render(request, 'shaxslar/detail.html', {
        'shaxs':       shaxs,
        'murojaatlar': murojaatlar,
        'yordamlar':   yordamlar,
        'yordam_soni': yordamlar.count(),
        'pul_summa':   pul_summa,
        **_shared_context(request),
    })


@can_edit_required
def yordam_create(request, shaxs_pk):
    shaxs = get_object_or_404(Shaxs, pk=shaxs_pk)

    # ?murojaat=<id> bilan kelgan bo'lsak — formada o'shani belgilab qo'yamiz
    # va saqlangandan keyin o'sha murojaat sahifasiga qaytamiz.
    initial = {'sana': date.today()}
    prefill_murojaat_id = request.GET.get('murojaat')
    if prefill_murojaat_id and prefill_murojaat_id.isdigit():
        if shaxs.murojaatlar.filter(pk=prefill_murojaat_id).exists():
            initial['murojaat'] = prefill_murojaat_id

    if request.method == 'POST':
        form = YordamForm(request.POST, shaxs=shaxs)
        if form.is_valid():
            yordam = form.save(commit=False)
            yordam.shaxs = shaxs
            yordam.qabul_qilgan = request.user
            yordam.save()
            messages.success(
                request,
                f"✅ {yordam.bergan_fio} dan yordam qayd etildi."
            )
            if yordam.murojaat_id:
                return redirect('murojaat_detail', pk=yordam.murojaat_id)
            return redirect('shaxs_detail', pk=shaxs.pk)
    else:
        form = YordamForm(initial=initial, shaxs=shaxs)

    return render(request, 'shaxslar/yordam_form.html', {
        'shaxs': shaxs,
        'form':  form,
        **_shared_context(request),
    })


@admin_required
def yordam_delete(request, pk):
    yordam = get_object_or_404(Yordam.objects.select_related('shaxs'), pk=pk)
    shaxs_pk = yordam.shaxs_id

    if request.method == 'POST':
        yordam.delete()
        messages.success(request, "Yordam yozuvi o'chirildi.")
        return redirect('shaxs_detail', pk=shaxs_pk)

    return render(request, 'shaxslar/yordam_delete_confirm.html', {
        'yordam': yordam,
        **_shared_context(request),
    })


# ─── Users (admin-only) ────────────────────────────────────────────────────────

@admin_required
def users_list(request):
    users = (
        User.objects
        .select_related('profile')
        .order_by('last_name', 'first_name')
    )
    return render(request, 'users/list.html', {
        'users': users,
        **_shared_context(request),
    })


@admin_required
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(
            request,
            f"✅ Hodim qo'shildi. Web kirishi uchun login: «{user.username}»."
        )
        return redirect('users_list')
    return render(request, 'users/create.html', {
        'form': form,
        **_shared_context(request),
    })


@admin_required
def user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    form = UserEditForm(request.POST or None, instance=user_obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"✅ {user_obj.username} ma'lumotlari yangilandi.")
        return redirect('users_list')
    return render(request, 'users/edit.html', {
        'form': form,
        'edited_user': user_obj,
        **_shared_context(request),
    })
