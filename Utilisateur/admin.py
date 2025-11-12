from django.contrib import admin  # ← AJOUTER CETTE LIGNE
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import (
    Section, CustomUser, Professeur,
    Comptable
)

# ========================================
# CONFIGURATION ADMIN - SECTION
# ========================================

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = [
        'nom', 'adresse_courte', 'telephone', 'email',
        'responsable_nom', 'professeurs_count', 'classes_count',
        'is_active_badge', 'created_at'
    ]
    list_filter = ['is_active', 'created_at', 'nom']
    search_fields = ['nom', 'adresse', 'responsable_nom', 'email', 'telephone']
    readonly_fields = ['created_at', 'updated_at', 'professeurs_count', 'classes_count']
    fieldsets = (
        ('Informations principales', {
            'fields': ('nom', 'adresse', 'is_active')
        }),
        ('Contact', {
            'fields': ('telephone', 'email', 'responsable_nom')
        }),
        ('Statistiques', {
            'fields': ('professeurs_count', 'classes_count'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['activer_sections', 'desactiver_sections']
    date_hierarchy = 'created_at'
    
    def adresse_courte(self, obj):
        """Affiche une version courte de l'adresse"""
        return obj.adresse[:50] + '...' if len(obj.adresse) > 50 else obj.adresse
    adresse_courte.short_description = 'Adresse'
    
    def is_active_badge(self, obj):
        """Badge coloré pour le statut actif"""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">✓ Active</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">✗ Inactive</span>'
        )
    is_active_badge.short_description = 'Statut'
    
    def professeurs_count(self, obj):
        """Nombre de professeurs"""
        count = obj.get_professeurs_count()
        return format_html('<strong>{}</strong>', count)
    professeurs_count.short_description = 'Professeurs'
    
    def classes_count(self, obj):
        """Nombre de classes"""
        count = obj.get_classes_count()
        return format_html('<strong>{}</strong>', count)
    classes_count.short_description = 'Classes'
    
    @admin.action(description='Activer les sections sélectionnées')
    def activer_sections(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} section(s) activée(s) avec succès.',
            messages.SUCCESS
        )
    
    @admin.action(description='Désactiver les sections sélectionnées')
    def desactiver_sections(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} section(s) désactivée(s) avec succès.',
            messages.WARNING
        )


# ========================================
# CONFIGURATION ADMIN - PROFESSEUR
# ========================================
# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Professeur, CustomUser, Comptable


@admin.register(Professeur)
class ProfesseurAdmin(admin.ModelAdmin):
    """Administration des professeurs avec gestion des documents"""
    
    list_display = [
        'matricule', 'get_full_name', 'grade', 'statut',
        'get_sections_count', 'documents_status', 'is_active',
        'created_at'
    ]
    
    list_filter = [
        'grade', 'statut', 'genre', 'is_active',
        'created_at', 'situation_matrimoniale'
    ]
    
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'matricule', 'numero_cni', 'specialite'
    ]
    
    readonly_fields = [
        'matricule', 'date_embauche', 'created_at', 'updated_at',
        'photo_uploaded_at', 'cni_uploaded_at', 'rib_uploaded_at',
        'cv_uploaded_at', 'diplome_uploaded_at',
        'display_photo', 'documents_summary'
    ]
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('user', 'matricule', 'is_active')
        }),
        ('Informations personnelles', {
            'fields': (
                'date_naissance', 'genre', 'nationalite', 'numero_cni',
                'situation_matrimoniale', 'domicile'
            )
        }),
        ('Informations professionnelles', {
            'fields': (
                'grade', 'statut', 'specialite', 'diplome',
                'annee_experience', 'sections', 'section_active'
            )
        }),
        ('Documents', {
            'fields': (
                'display_photo', 'photo', 'photo_uploaded_at',
                'cni_document', 'cni_uploaded_at',
                'rib_document', 'rib_uploaded_at',
                'cv_document', 'cv_uploaded_at',
                'diplome_document', 'diplome_uploaded_at',
                'documents_summary'
            ),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('date_embauche', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    filter_horizontal = ['sections']
    
    def get_full_name(self, obj):
        """Afficher le nom complet"""
        return obj.user.get_full_name()
    get_full_name.short_description = 'Nom complet'
    get_full_name.admin_order_field = 'user__last_name'
    
    def get_sections_count(self, obj):
        """Nombre de sections"""
        count = obj.sections.count()
        return format_html(
            '<span style="background-color: #1e3c72; color: white; '
            'padding: 3px 10px; border-radius: 10px;">{}</span>',
            count
        )
    get_sections_count.short_description = 'Sections'
    
    def documents_status(self, obj):
        """Statut des documents"""
        if obj.has_complete_documents():
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Complet</span>'
            )
        else:
            missing_count = len(obj.get_missing_documents())
            return format_html(
                '<span style="color: orange; font-weight: bold;">⚠ {} manquant(s)</span>',
                missing_count
            )
    documents_status.short_description = 'Documents'
    
    def display_photo(self, obj):
        """Afficher la photo dans l'admin"""
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 150px; '
                'border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />',
                obj.photo.url
            )
        return format_html('<span style="color: #999;">Aucune photo</span>')
    display_photo.short_description = 'Photo'
    
    def documents_summary(self, obj):
        """Résumé des documents"""
        docs = [
            ('Photo', obj.photo, obj.photo_uploaded_at),
            ('CNI', obj.cni_document, obj.cni_uploaded_at),
            ('RIB', obj.rib_document, obj.rib_uploaded_at),
            ('CV', obj.cv_document, obj.cv_uploaded_at),
            ('Diplôme', obj.diplome_document, obj.diplome_uploaded_at),
        ]
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #f5f5f5; font-weight: bold;">'
        html += '<th style="padding: 8px; text-align: left;">Document</th>'
        html += '<th style="padding: 8px; text-align: center;">Statut</th>'
        html += '<th style="padding: 8px; text-align: left;">Date</th>'
        html += '<th style="padding: 8px; text-align: center;">Actions</th>'
        html += '</tr>'
        
        for name, doc, uploaded_at in docs:
            html += '<tr style="border-bottom: 1px solid #ddd;">'
            html += f'<td style="padding: 8px;">{name}</td>'
            
            if doc:
                html += '<td style="padding: 8px; text-align: center;">'
                html += '<span style="color: green;">✓</span></td>'
                html += f'<td style="padding: 8px;">{uploaded_at.strftime("%d/%m/%Y %H:%M") if uploaded_at else "N/A"}</td>'
                html += '<td style="padding: 8px; text-align: center;">'
                html += f'<a href="{doc.url}" target="_blank" style="color: #1e3c72;">📥 Télécharger</a>'
                html += '</td>'
            else:
                html += '<td style="padding: 8px; text-align: center;">'
                html += '<span style="color: red;">✗</span></td>'
                html += '<td style="padding: 8px; color: #999;">-</td>'
                html += '<td style="padding: 8px; text-align: center; color: #999;">-</td>'
            
            html += '</tr>'
        
        html += '</table>'
        
        return mark_safe(html)
    documents_summary.short_description = 'Résumé des documents'
    
    actions = ['marquer_actif', 'marquer_inactif', 'exporter_professeurs_sans_documents']
    
    def marquer_actif(self, request, queryset):
        """Marquer comme actif"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} professeur(s) marqué(s) comme actif(s).')
    marquer_actif.short_description = "Marquer comme actif"
    
    def marquer_inactif(self, request, queryset):
        """Marquer comme inactif"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} professeur(s) marqué(s) comme inactif(s).')
    marquer_inactif.short_description = "Marquer comme inactif"
    
    def exporter_professeurs_sans_documents(self, request, queryset):
        """Exporter les professeurs avec documents incomplets"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="professeurs_documents_incomplets.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Matricule', 'Nom', 'Email', 'Documents manquants'
        ])
        
        for prof in queryset:
            if not prof.has_complete_documents():
                missing = ', '.join(prof.get_missing_documents())
                writer.writerow([
                    prof.matricule,
                    prof.user.get_full_name(),
                    prof.user.email,
                    missing
                ])
        
        return response
    exporter_professeurs_sans_documents.short_description = "Exporter professeurs sans documents complets"


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    """Administration des utilisateurs"""
    
    list_display = [
        'email', 'get_full_name', 'role', 'section_principale',
        'is_active_user', 'is_staff', 'date_joined'
    ]
    
    list_filter = ['role', 'is_active_user', 'is_staff', 'date_joined']
    
    search_fields = ['email', 'first_name', 'last_name']
    
    readonly_fields = ['date_joined', 'last_login']
    
    fieldsets = (
        ('Authentification', {
            'fields': ('email', 'password')
        }),
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'telephone')
        }),
        ('Permissions', {
            'fields': (
                'role', 'section_principale', 'sections_autorisees',
                'is_active_user', 'is_staff', 'is_superuser'
            )
        }),
        ('Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    filter_horizontal = ['sections_autorisees', 'groups', 'user_permissions']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Nom complet'
    get_full_name.admin_order_field = 'last_name'


# ========================================
# CONFIGURATION ADMIN - COMPTABLE
# ========================================

@admin.register(Comptable)
class ComptableAdmin(admin.ModelAdmin):
    list_display = [
        'matricule', 'code_unique', 'nom_complet_display',
        'email_display', 'age_display', 'statut_badge',
        'derniere_connexion', 'created_at'
    ]
    list_filter = [
        'is_active', 'created_at', 'user__is_active',
        'user__last_login'
    ]
    search_fields = [
        'matricule', 'code_unique', 'user__first_name',
        'user__last_name', 'user__email'
    ]
    readonly_fields = [
        'matricule', 'code_unique', 'nom_complet_display',
        'email_display', 'age_display', 'anciennete_display',
        'statut_complet', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('user',)
        }),
        ('Informations professionnelles', {
            'fields': ('matricule', 'code_unique', 'is_active')
        }),
        ('Informations personnelles', {
            'fields': ('date_naissance', 'age_display')
        }),
        ('Informations calculées', {
            'fields': (
                'nom_complet_display', 'email_display',
                'statut_complet', 'anciennete_display'
            ),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'activer_comptables', 'desactiver_comptables',
        'afficher_statistiques'
    ]
    
    def nom_complet_display(self, obj):
        """Nom complet du comptable"""
        return obj.get_nom_complet() or '-'
    nom_complet_display.short_description = 'Nom complet'
    
    def email_display(self, obj):
        """Email du comptable"""
        email = obj.get_email()
        if email:
            return format_html('<a href="mailto:{}">{}</a>', email, email)
        return '-'
    email_display.short_description = 'Email'
    
    def age_display(self, obj):
        """Affichage de l'âge"""
        return obj.get_age_display()
    age_display.short_description = 'Âge'
    
    def statut_badge(self, obj):
        """Badge coloré pour le statut"""
        statut = obj.get_statut_display()
        color = obj.get_statut_color()
        colors_map = {
            'success': '#28a745',
            'warning': '#ffc107',
            'danger': '#dc3545'
        }
        bg_color = colors_map.get(color, '#6c757d')
        text_color = 'white' if color != 'warning' else 'black'
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 3px;">{}</span>',
            bg_color, text_color, statut
        )
    statut_badge.short_description = 'Statut'
    
    def derniere_connexion(self, obj):
        """Dernière connexion de l'utilisateur"""
        last_login = obj.get_derniere_connexion()
        if last_login:
            return last_login.strftime('%d/%m/%Y %H:%M')
        return 'Jamais'
    derniere_connexion.short_description = 'Dernière connexion'
    
    def anciennete_display(self, obj):
        """Affichage de l'ancienneté"""
        annees = obj.anciennete_annees
        return f'{annees:.1f} ans ({obj.anciennete_jours} jours)'
    anciennete_display.short_description = 'Ancienneté'
    
    def statut_complet(self, obj):
        """Statut complet avec détails"""
        html = f"""
        <table style="border-collapse: collapse;">
            <tr>
                <td style="padding: 5px;"><strong>Comptable actif:</strong></td>
                <td style="padding: 5px;">{'✓ Oui' if obj.is_active else '✗ Non'}</td>
            </tr>
            <tr>
                <td style="padding: 5px;"><strong>Utilisateur actif:</strong></td>
                <td style="padding: 5px;">{'✓ Oui' if obj.is_user_active() else '✗ Non'}</td>
            </tr>
            <tr>
                <td style="padding: 5px;"><strong>Pleinement actif:</strong></td>
                <td style="padding: 5px;">{'✓ Oui' if obj.is_fully_active() else '✗ Non'}</td>
            </tr>
            <tr>
                <td style="padding: 5px;"><strong>Connecté récemment:</strong></td>
                <td style="padding: 5px;">{'✓ Oui' if obj.est_connecte_recemment() else '✗ Non'}</td>
            </tr>
        </table>
        """
        return format_html(html)
    statut_complet.short_description = 'Statut détaillé'
    
    @admin.action(description='Activer les comptables sélectionnés')
    def activer_comptables(self, request, queryset):
        count = 0
        for comptable in queryset:
            comptable.activer()
            count += 1
        self.message_user(
            request,
            f'{count} comptable(s) activé(s) avec succès.',
            messages.SUCCESS
        )
    
    @admin.action(description='Désactiver les comptables sélectionnés')
    def desactiver_comptables(self, request, queryset):
        count = 0
        for comptable in queryset:
            comptable.desactiver()
            count += 1
        self.message_user(
            request,
            f'{count} comptable(s) désactivé(s) avec succès.',
            messages.WARNING
        )
    
    @admin.action(description='Afficher les statistiques')
    def afficher_statistiques(self, request, queryset):
        stats = Comptable.statistiques()
        message = f"""
        Statistiques des comptables:
        - Total: {stats['total']}
        - Actifs: {stats['actifs']}
        - Inactifs: {stats['inactifs']}
        - Pleinement actifs: {stats['pleinement_actifs']}
        - Avec email: {stats['avec_email']}
        - Connectés récemment: {stats['connectes_recemment']}
        """
        self.message_user(request, message, messages.INFO)


# ========================================
# PERSONNALISATION DU SITE ADMIN
# ========================================

admin.site.site_header = "MyPEDAGO - IIPEA"
admin.site.site_title = "MyPEDAGO - IIPEA"
admin.site.index_title = "Tableau de bord d'administration"