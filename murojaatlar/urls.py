from django.urls import path

from . import views


urlpatterns = [
    # ── Auth ──
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── Dashboard ──
    path('', views.dashboard, name='dashboard'),

    # ── Murojaatlar ──
    path('murojaatlar/',                       views.murojaat_list,   name='murojaat_list'),
    path('murojaatlar/yangi/',                 views.murojaat_create, name='murojaat_create'),
    path('murojaatlar/<int:pk>/',              views.murojaat_detail, name='murojaat_detail'),
    path('murojaatlar/<int:pk>/tahrir/',       views.murojaat_edit,   name='murojaat_edit'),
    path('murojaatlar/<int:pk>/ochir/',        views.murojaat_delete, name='murojaat_delete'),

    # ── Shaxslar ──
    path('shaxslar/',                              views.shaxslar_list,  name='shaxslar_list'),
    path('shaxslar/<int:pk>/',                     views.shaxs_detail,   name='shaxs_detail'),
    path('shaxslar/<int:shaxs_pk>/yordam/yangi/',  views.yordam_create,  name='yordam_create'),
    path('yordam/<int:pk>/ochir/',                 views.yordam_delete,  name='yordam_delete'),

    # ── Users (admin) ──
    path('foydalanuvchilar/',                 views.users_list, name='users_list'),
    path('foydalanuvchilar/yangi/',           views.user_create, name='user_create'),
    path('foydalanuvchilar/<int:pk>/tahrir/', views.user_edit,   name='user_edit'),
]
