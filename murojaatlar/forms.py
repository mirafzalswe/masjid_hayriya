"""
Forms — input validation and serialisation boundary.

Phone numbers are normalised in `clean_telefon` so the same logic is enforced
whether data comes from the web, the bot, or an admin import.
"""
from __future__ import annotations

import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from .models import Murojaat, Priority, Shaxs, UserProfile, Yordam, normalize_phone


_PHONE_INPUT_RE = re.compile(r'[\d+\-\s()]+$')


def _validate_phone(raw: str) -> str:
    if not raw:
        raise forms.ValidationError("Telefon raqami kiritilmagan.")
    if not _PHONE_INPUT_RE.match(raw):
        raise forms.ValidationError("Telefonda faqat raqam, +, -, bo'sh joy va qavslar bo'lishi mumkin.")
    canonical = normalize_phone(raw)
    if len(canonical) < 9 or len(canonical) > 15:
        raise forms.ValidationError("Telefon raqami noto'g'ri uzunlikda. Misol: +998 90 123 45 67")
    return canonical


# ─── Auth ──────────────────────────────────────────────────────────────────────

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Foydalanuvchi nomi",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'username',
            'autocomplete': 'username',
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        label="Parol",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
        }),
    )


# ─── Domain ────────────────────────────────────────────────────────────────────

class ShaxsForm(forms.ModelForm):
    class Meta:
        model = Shaxs
        fields = ['fio', 'telefon', 'manzil', 'qoshimcha_ma_lumot']
        widgets = {
            'fio':                forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Familiya Ism Otasining ismi'}),
            'telefon':            forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+998 90 123 45 67', 'inputmode': 'tel'}),
            'manzil':             forms.TextInput(attrs={'class': 'form-input', 'placeholder': "Tuman, mahalla, ko'cha"}),
            'qoshimcha_ma_lumot': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': "Oila a'zolari, ish holati..."}),
        }

    def clean_fio(self):
        fio = self.cleaned_data['fio'].strip()
        if len(fio) < 5:
            raise forms.ValidationError("F.I.O kamida 5 ta belgidan iborat bo'lsin.")
        return fio

    def clean_telefon(self):
        return _validate_phone(self.cleaned_data['telefon'])


class MurojaatForm(forms.ModelForm):
    class Meta:
        model = Murojaat
        fields = ['shaxs', 'muhtojlik_turi', 'mazmun', 'priority', 'murojaat_sanasi', 'izoh']
        widgets = {
            'shaxs':           forms.Select(attrs={'class': 'form-input'}),
            'muhtojlik_turi':  forms.Select(attrs={'class': 'form-input'}),
            'mazmun':          forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'minlength': 10}),
            'priority':        forms.Select(attrs={'class': 'form-input'}),
            'murojaat_sanasi': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'izoh':            forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default for new records: today + medium priority. The template
        # sets value="{% now %}" too — this is the server-side guarantee.
        if not self.instance.pk:
            self.fields['priority'].initial = Priority.ORTA

    def clean_mazmun(self):
        mazmun = self.cleaned_data['mazmun'].strip()
        if len(mazmun) < 10:
            raise forms.ValidationError("Murojaat mazmuni kamida 10 ta belgidan iborat bo'lsin.")
        return mazmun


class YordamBerForm(forms.ModelForm):
    class Meta:
        model = Murojaat
        fields = ['holat', 'yordam_sanasi', 'yordam_turi', 'yordam_miqdori', 'mas_ul_hodim', 'izoh']
        widgets = {
            'holat':          forms.Select(attrs={'class': 'form-input'}),
            'yordam_sanasi':  forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'yordam_turi':    forms.TextInput(attrs={'class': 'form-input', 'placeholder': "Masalan: Oziq-ovqat to'plami"}),
            'yordam_miqdori': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0', 'min': 0, 'inputmode': 'numeric'}),
            'mas_ul_hodim':   forms.Select(attrs={'class': 'form-input'}),
            'izoh':           forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }


class YordamForm(forms.ModelForm):
    """Bir shaxsga berilgan konkret yordam (pul/mahsulot/xizmat).

    `shaxs` URL'dan, `qabul_qilgan` request.user'dan keladi — formada
    ko'rinmaydi.
    """

    class Meta:
        model = Yordam
        fields = ['turi', 'miqdor', 'mazmun', 'bergan_fio', 'bergan_telefon',
                  'sana', 'murojaat']
        widgets = {
            'turi':           forms.Select(attrs={'class': 'form-input'}),
            'miqdor':         forms.NumberInput(attrs={'class': 'form-input',
                                                       'placeholder': "Masalan: 200000",
                                                       'min': 0, 'inputmode': 'numeric'}),
            'mazmun':         forms.Textarea(attrs={'class': 'form-input', 'rows': 3,
                                                    'placeholder': "Tafsilot: nima berildi, qancha…"}),
            'bergan_fio':     forms.TextInput(attrs={'class': 'form-input',
                                                     'placeholder': "Familiya Ism (ixtiyoriy)"}),
            'bergan_telefon': forms.TextInput(attrs={'class': 'form-input',
                                                     'placeholder': '+998 90 123 45 67',
                                                     'inputmode': 'tel'}),
            'sana':           forms.DateInput(attrs={'class': 'form-input', 'type': 'date'},
                                              format='%Y-%m-%d'),
            'murojaat':       forms.Select(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, shaxs: Shaxs | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        # Kim berdi nomi — ixtiyoriy, anonim xayriya ham bo'lishi mumkin.
        self.fields['bergan_fio'].required = False
        # Murojaat tanlovini faqat shu shaxs murojaatlari bilan cheklab qo'yamiz.
        if shaxs is not None:
            self.fields['murojaat'].queryset = shaxs.murojaatlar.order_by('-murojaat_sanasi')
            self.fields['murojaat'].empty_label = "— Umumiy yordam (murojaatsiz) —"
        else:
            self.fields['murojaat'].queryset = Murojaat.objects.none()

    def clean_bergan_fio(self):
        fio = (self.cleaned_data.get('bergan_fio') or '').strip()
        if fio and len(fio) < 3:
            raise forms.ValidationError("Ism juda qisqa (kamida 3 belgi) yoki bo'sh qoldiring.")
        return fio or "Noma'lum"

    def clean_bergan_telefon(self):
        raw = (self.cleaned_data.get('bergan_telefon') or '').strip()
        if not raw:
            return ''
        return _validate_phone(raw)

    def clean(self):
        cleaned = super().clean()
        turi = cleaned.get('turi')
        miqdor = cleaned.get('miqdor')
        mazmun = (cleaned.get('mazmun') or '').strip()
        # Pulda — miqdor majburiy. Boshqa turlarda — kamida miqdor yoki tavsif bo'lsin.
        if turi == 'pul' and not miqdor:
            self.add_error('miqdor', "Pul yordami uchun miqdor majburiy.")
        elif turi != 'pul' and not miqdor and not mazmun:
            self.add_error('mazmun', "Mahsulot/xizmat yordami uchun tavsif yoki miqdor kiriting.")
        return cleaned


# ─── User management ───────────────────────────────────────────────────────────

class _UserBaseMixin:
    """Shared field definitions for user create/edit forms."""

    role = forms.ChoiceField(
        choices=[],  # populated in __init__ from Role enum
        widget=forms.Select(attrs={'class': 'form-input'}),
        label="Rol",
    )
    telefon = forms.CharField(
        max_length=32, required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+998 90 123 45 67'}),
    )
    telegram_id = forms.IntegerField(
        required=False, label="Telegram ID",
        widget=forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Masalan: 123456789'}),
        help_text="Bot orqali kirish uchun. /start bosilganda ID ko'rinadi.",
    )

    def clean_telefon(self):
        raw = self.cleaned_data.get('telefon', '').strip()
        if not raw:
            return ''
        return _validate_phone(raw)

    def clean_telegram_id(self):
        tg_id = self.cleaned_data.get('telegram_id')
        if tg_id is None:
            return None
        qs = UserProfile.objects.filter(telegram_id=tg_id)
        # Exclude the row we are editing.
        instance = getattr(self, 'instance', None)
        if instance is not None and instance.pk:
            qs = qs.exclude(user_id=instance.pk)
        if qs.exists():
            raise forms.ValidationError("Bu Telegram ID boshqa foydalanuvchiga biriktirilgan.")
        return tg_id


class UserCreateForm(_UserBaseMixin, forms.Form):
    """Sodda hodim qo'shish formasi.

    F.I.O bitta maydon — saqlashda first_name/last_name ga ajratiladi.
    Telegram ID majburiy (bot orqali kirish uchun kalit). Username avtomatik
    `tg<telegram_id>` shaklida yaratiladi va unique bo'lishi kafolatlanadi.
    """

    fio = forms.CharField(
        max_length=200, label="F.I.O",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Familiya Ism Otasining ismi',
            'autofocus': True,
            'autocomplete': 'name',
        }),
    )
    telegram_id = forms.IntegerField(
        label="Telegram ID",
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Masalan: 123456789',
            'inputmode': 'numeric',
        }),
        help_text="Hodim botda /start bosganda ID ko'rsatiladi.",
    )
    role = forms.ChoiceField(
        choices=[], label="Rol",
        widget=forms.Select(attrs={'class': 'form-input'}),
    )
    telefon = forms.CharField(
        max_length=32, required=False, label="Telefon (ixtiyoriy)",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+998 90 123 45 67',
            'inputmode': 'tel',
        }),
    )
    password = forms.CharField(
        label="Parol",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'autocomplete': 'new-password',
            'placeholder': "Kamida 6 ta belgi",
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Role  # local to avoid circular import
        self.fields['role'].choices = Role.choices

    def clean_fio(self):
        fio = (self.cleaned_data.get('fio') or '').strip()
        if len(fio) < 5:
            raise forms.ValidationError("F.I.O kamida 5 ta belgidan iborat bo'lsin.")
        return fio

    def clean_password(self):
        pwd = self.cleaned_data.get('password') or ''
        if len(pwd) < 6:
            raise forms.ValidationError("Parol kamida 6 ta belgidan iborat bo'lsin.")
        return pwd

    def _generate_username(self, tg_id: int) -> str:
        base = f"tg{tg_id}"
        username, n = base, 1
        while User.objects.filter(username=username).exists():
            n += 1
            username = f"{base}_{n}"
        return username

    def save(self):
        fio = self.cleaned_data['fio']
        # «Familiya Ism …» — birinchi so'z familiya, qolgani ism.
        parts = fio.split(None, 1)
        last_name = parts[0][:150]
        first_name = (parts[1] if len(parts) > 1 else '')[:150]

        tg_id = self.cleaned_data['telegram_id']
        user = User.objects.create_user(
            username=self._generate_username(tg_id),
            password=self.cleaned_data['password'],
            first_name=first_name,
            last_name=last_name,
        )
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'role':        self.cleaned_data['role'],
                'telefon':     self.cleaned_data.get('telefon', ''),
                'telegram_id': tg_id,
            },
        )
        return user


class UserEditForm(_UserBaseMixin, forms.ModelForm):
    new_password = forms.CharField(
        required=False, label="Yangi parol",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': "O'zgartirmasangiz bo'sh qoldiring",
            'autocomplete': 'new-password',
        }),
        help_text="Bo'sh qoldirilsa parol o'zgarmaydi.",
    )
    role = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-input'}),
        label="Rol",
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-input'}),
            'email':      forms.EmailInput(attrs={'class': 'form-input'}),
            'is_active':  forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Role
        self.fields['role'].choices = Role.choices
        if self.instance and getattr(self.instance, 'profile', None):
            p = self.instance.profile
            self.fields['role'].initial        = p.role
            self.fields['telefon'].initial     = p.telefon
            self.fields['telegram_id'].initial = p.telegram_id

    def clean_new_password(self):
        pwd = (self.cleaned_data.get('new_password') or '').strip()
        if pwd and len(pwd) < 6:
            raise forms.ValidationError("Parol kamida 6 ta belgidan iborat bo'lsin.")
        return pwd

    def save(self, commit=True):
        user = super().save(commit=False)
        new_pwd = self.cleaned_data.get('new_password')
        if new_pwd:
            user.set_password(new_pwd)
        if commit:
            user.save()
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'role':        self.cleaned_data['role'],
                    'telefon':     self.cleaned_data.get('telefon', ''),
                    'telegram_id': self.cleaned_data.get('telegram_id'),
                },
            )
        return user
