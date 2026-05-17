from django.contrib import admin
from django.utils.html import format_html

from .models import Murojaat, Shaxs, UserProfile, Yordam


@admin.register(Shaxs)
class ShaxsAdmin(admin.ModelAdmin):
    list_display = ['fio', 'telefon', 'manzil', 'murojaatlar_count', 'yaratilgan']
    search_fields = ['fio', 'telefon']
    list_per_page = 50
    readonly_fields = ['yaratilgan']

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('murojaatlar')

    @admin.display(description="Murojaatlar", ordering='murojaatlar__count')
    def murojaatlar_count(self, obj):
        return obj.murojaatlar.count()


@admin.register(Murojaat)
class MurojaatAdmin(admin.ModelAdmin):
    list_display = ['id', 'shaxs', 'muhtojlik_turi', 'priority_badge', 'holat_badge',
                    'murojaat_sanasi', 'yaratilgan']
    list_filter = ['holat', 'priority', 'muhtojlik_turi', 'murojaat_sanasi']
    search_fields = ['shaxs__fio', 'shaxs__telefon', 'mazmun']
    date_hierarchy = 'murojaat_sanasi'
    list_per_page = 50
    list_select_related = ['shaxs', 'mas_ul_hodim']
    autocomplete_fields = ['shaxs', 'mas_ul_hodim']
    readonly_fields = ['yaratilgan', 'yangilangan', 'telegram_id', 'telegram_username']
    fieldsets = (
        ("Murojaat", {
            'fields': ('shaxs', 'muhtojlik_turi', 'mazmun', 'priority', 'holat',
                       'murojaat_sanasi', 'izoh'),
        }),
        ("Yordam", {
            'fields': ('yordam_sanasi', 'yordam_turi', 'yordam_miqdori', 'mas_ul_hodim'),
        }),
        ("Telegram", {
            'classes': ('collapse',),
            'fields': ('telegram_id', 'telegram_username'),
        }),
        ("Tizim", {
            'classes': ('collapse',),
            'fields': ('yaratilgan', 'yangilangan'),
        }),
    )

    @admin.display(description="Muhimlik", ordering='priority')
    def priority_badge(self, obj):
        colors = {1: '#ef4444', 2: '#f59e0b', 3: '#22c55e'}
        return format_html(
            '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;'
            'background:{};margin-right:6px;vertical-align:middle;"></span>{}',
            colors.get(obj.priority, '#999'),
            obj.get_priority_display(),
        )

    @admin.display(description="Holat", ordering='holat')
    def holat_badge(self, obj):
        return obj.get_holat_display()


@admin.register(Yordam)
class YordamAdmin(admin.ModelAdmin):
    list_display = ['sana', 'shaxs', 'bergan_fio', 'turi', 'miqdor', 'qabul_qilgan']
    list_filter = ['turi', 'sana']
    search_fields = ['shaxs__fio', 'shaxs__telefon', 'bergan_fio', 'bergan_telefon', 'mazmun']
    date_hierarchy = 'sana'
    autocomplete_fields = ['shaxs', 'murojaat', 'qabul_qilgan']
    list_select_related = ['shaxs', 'qabul_qilgan']
    readonly_fields = ['yaratilgan']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'telefon', 'telegram_id']
    list_filter = ['role']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'telefon']
    autocomplete_fields = ['user']
    list_select_related = ['user']
