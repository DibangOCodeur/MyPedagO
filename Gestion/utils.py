# utils.py - Utilitaires pour le système de gestion des contrats

from django.http import HttpResponse
from django.template.loader import render_to_string, get_template
from django.utils import timezone
from io import BytesIO
import pandas as pd
from decimal import Decimal

# Pour la génération de PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image, PageBreak
)
from reportlab.pdfgen import canvas


# ==========================================
# GÉNÉRATION DE PDF - FICHE DE CONTRAT
# ==========================================

def generate_fiche_contrat_pdf(contrat):
    """
    Génère la fiche de contrat en PDF
    
    Contient:
    - Informations du professeur
    - Informations de la classe et du module
    - Volumes horaires (CM, TD, TP)
    - Taux horaires
    - Montant total contractuel
    - Dates
    - Signatures
    """
    buffer = BytesIO()
    
    # Créer le document PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Conteneur pour les éléments du PDF
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=1,  # Centré
    )
    
    # En-tête
    logo_path = 'static/images/logo_iipea.png'  # Ajuster le chemin
    try:
        logo = Image(logo_path, width=3*cm, height=3*cm)
        elements.append(logo)
        elements.append(Spacer(1, 0.5*cm))
    except:
        pass  # Si le logo n'existe pas
    
    # Titre
    title = Paragraph("FICHE DE CONTRAT D'ENSEIGNEMENT", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.5*cm))
    
    # Numéro de contrat et date
    info_contrat = f"<b>Contrat N°:</b> {contrat.id} | <b>Date:</b> {contrat.date_validation.strftime('%d/%m/%Y')}"
    elements.append(Paragraph(info_contrat, styles['Normal']))
    elements.append(Spacer(1, 0.8*cm))
    
    # Section 1: Informations du professeur
    elements.append(Paragraph("<b>1. INFORMATIONS DU PROFESSEUR</b>", styles['Heading2']))
    elements.append(Spacer(1, 0.3*cm))
    
    prof_data = [
        ['Nom complet:', f"{contrat.professeur.user.get_full_name()}"],
        ['Grade:', contrat.professeur.grade if hasattr(contrat.professeur, 'grade') else '-'],
        ['Spécialité:', contrat.professeur.specialite if hasattr(contrat.professeur, 'specialite') else '-'],
        ['Contact:', contrat.professeur.user.email],
    ]
    
    prof_table = Table(prof_data, colWidths=[4*cm, 12*cm])
    prof_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(prof_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # Section 2: Informations du module
    elements.append(Paragraph("<b>2. INFORMATIONS DU MODULE</b>", styles['Heading2']))
    elements.append(Spacer(1, 0.3*cm))
    
    module_data = [
        ['Classe:', contrat.classe.nom],
        ['Département:', contrat.classe.departement],
        ['Module:', f"{contrat.maquette.filiere_sigle} - {contrat.maquette.niveau_libelle}"],
        ['Année académique:', contrat.maquette.annee_academique],
        ['Type d\'enseignement:', contrat.get_type_enseignement_display()],
    ]
    
    if contrat.type_enseignement == 'TRONC_COMMUN':
        classes_tc = ', '.join([c.nom for c in contrat.classes_tronc_commun.all()])
        module_data.append(['Classes en tronc commun:', classes_tc])
    
    module_table = Table(module_data, colWidths=[4*cm, 12*cm])
    module_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(module_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # Section 3: Volumes et taux horaires
    elements.append(Paragraph("<b>3. VOLUMES ET TAUX HORAIRES</b>", styles['Heading2']))
    elements.append(Spacer(1, 0.3*cm))
    
    volumes_data = [
        ['Type', 'Volume (heures)', 'Taux horaire (FCFA)', 'Montant (FCFA)'],
        [
            'Cours Magistral (CM)',
            f"{contrat.volume_heure_cours}",
            f"{contrat.taux_horaire_cours:,.0f}",
            f"{contrat.volume_heure_cours * contrat.taux_horaire_cours:,.0f}"
        ],
        [
            'Travaux Dirigés (TD)',
            f"{contrat.volume_heure_td}",
            f"{contrat.taux_horaire_td:,.0f}",
            f"{contrat.volume_heure_td * contrat.taux_horaire_td:,.0f}"
        ],
        [
            'Travaux Pratiques (TP)',
            f"{contrat.volume_heure_tp}",
            f"{contrat.taux_horaire_tp:,.0f}",
            f"{contrat.volume_heure_tp * contrat.taux_horaire_tp:,.0f}"
        ],
        [
            'TOTAL',
            f"<b>{contrat.volume_total_contractuel}</b>",
            '',
            f"<b>{contrat.montant_total_contractuel:,.0f}</b>"
        ],
    ]
    
    volumes_table = Table(volumes_data, colWidths=[4*cm, 3*cm, 4*cm, 5*cm])
    volumes_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90e2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(volumes_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # Section 4: Dates importantes
    elements.append(Paragraph("<b>4. DATES IMPORTANTES</b>", styles['Heading2']))
    elements.append(Spacer(1, 0.3*cm))
    
    dates_data = [
        ['Date de validation:', contrat.date_validation.strftime('%d/%m/%Y')],
        ['Date de début prévue:', contrat.date_debut_prevue.strftime('%d/%m/%Y') if contrat.date_debut_prevue else 'Non définie'],
        ['Date de fin prévue:', contrat.date_fin_prevue.strftime('%d/%m/%Y') if contrat.date_fin_prevue else 'Non définie'],
    ]
    
    dates_table = Table(dates_data, colWidths=[4*cm, 12*cm])
    dates_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(dates_table)
    elements.append(Spacer(1, 1*cm))
    
    # Section 5: Signatures
    elements.append(Paragraph("<b>5. SIGNATURES</b>", styles['Heading2']))
    elements.append(Spacer(1, 0.5*cm))
    
    signatures_data = [
        ['Le Professeur', 'Le Responsable RH', 'La Direction'],
        ['', '', ''],
        ['', '', ''],
        ['Signature:', 'Signature:', 'Signature:'],
    ]
    
    signatures_table = Table(signatures_data, colWidths=[5*cm, 5*cm, 5*cm])
    signatures_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -2), 30),
    ]))
    elements.append(signatures_table)
    
    # Pied de page
    elements.append(Spacer(1, 1*cm))
    footer_text = f"<i>Document généré le {timezone.now().strftime('%d/%m/%Y à %H:%M')}</i>"
    elements.append(Paragraph(footer_text, styles['Normal']))
    
    # Construire le PDF
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf


# ==========================================
# GÉNÉRATION DE PDF - REÇU DE PAIEMENT
# ==========================================

def generate_recu_paiement_pdf(paiement):
    """
    Génère un reçu de paiement en PDF
    """
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=1,
    )
    
    title = Paragraph("REÇU DE PAIEMENT", title_style)
    elements.append(title)
    elements.append(Spacer(1, 1*cm))
    
    # Informations du reçu
    recu_data = [
        ['N° Reçu:', f"R-{paiement.id:06d}"],
        ['Date de paiement:', paiement.date_paiement.strftime('%d/%m/%Y')],
        ['Mode de paiement:', paiement.get_mode_paiement_display()],
        ['Référence:', paiement.reference_paiement or '-'],
    ]
    
    recu_table = Table(recu_data, colWidths=[5*cm, 11*cm])
    recu_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(recu_table)
    elements.append(Spacer(1, 1*cm))
    
    # Bénéficiaire
    elements.append(Paragraph("<b>BÉNÉFICIAIRE</b>", styles['Heading2']))
    elements.append(Spacer(1, 0.3*cm))
    
    beneficiaire_data = [
        ['Nom complet:', paiement.professeur.user.get_full_name()],
        ['Contrat N°:', str(paiement.contrat.id)],
        ['Module:', f"{paiement.contrat.maquette.filiere_sigle} - {paiement.contrat.classe.nom}"],
    ]
    
    beneficiaire_table = Table(beneficiaire_data, colWidths=[5*cm, 11*cm])
    beneficiaire_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(beneficiaire_table)
    elements.append(Spacer(1, 1*cm))
    
    # Montants
    elements.append(Paragraph("<b>DÉTAIL DU PAIEMENT</b>", styles['Heading2']))
    elements.append(Spacer(1, 0.3*cm))
    
    montants_data = [
        ['Montant brut:', f"{paiement.montant_brut:,.0f} FCFA"],
        ['Déductions:', f"- {paiement.montant_deductions:,.0f} FCFA"],
        ['MONTANT NET PAYÉ:', f"<b>{paiement.montant_net:,.0f} FCFA</b>"],
    ]
    
    montants_table = Table(montants_data, colWidths=[8*cm, 8*cm])
    montants_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#4a90e2')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 14),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(montants_table)
    elements.append(Spacer(1, 2*cm))
    
    # Signature
    signature_text = "Signature du comptable: _______________________"
    elements.append(Paragraph(signature_text, styles['Normal']))
    
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf


# ==========================================
# EXPORTS EXCEL
# ==========================================

def export_contrats_to_excel(contrats, filename='contrats.xlsx'):
    """
    Exporte une liste de contrats vers Excel
    """
    # Préparer les données
    data = []
    for contrat in contrats:
        heures_effectuees = contrat.get_heures_effectuees()
        
        data.append({
            'ID': contrat.id,
            'Professeur': contrat.professeur.user.get_full_name(),
            'Classe': contrat.classe.nom,
            'Module': f"{contrat.maquette.filiere_sigle} - {contrat.maquette.niveau_libelle}",
            'Statut': contrat.get_status_display(),
            'Type': contrat.get_type_enseignement_display(),
            'Volume Cours (h)': float(contrat.volume_heure_cours),
            'Volume TD (h)': float(contrat.volume_heure_td),
            'Volume TP (h)': float(contrat.volume_heure_tp),
            'Volume Total (h)': float(contrat.volume_total_contractuel),
            'Heures Cours Effectuées': float(heures_effectuees['cours']),
            'Heures TD Effectuées': float(heures_effectuees['td']),
            'Heures TP Effectuées': float(heures_effectuees['tp']),
            'Heures Total Effectuées': float(contrat.volume_total_effectue),
            'Taux Réalisation (%)': round(contrat.taux_realisation, 2),
            'Montant Contractuel (FCFA)': float(contrat.montant_total_contractuel),
            'Montant À Payer (FCFA)': float(contrat.calculate_montant_a_payer()),
            'Date Validation': contrat.date_validation.strftime('%d/%m/%Y'),
            'Date Début': contrat.date_debut_reelle.strftime('%d/%m/%Y') if contrat.date_debut_reelle else '',
            'Date Fin': contrat.date_fin_reelle.strftime('%d/%m/%Y') if contrat.date_fin_reelle else '',
            'Support Cours': 'Oui' if contrat.support_cours_uploaded else 'Non',
            'Syllabus': 'Oui' if contrat.syllabus_uploaded else 'Non',
        })
    
    # Créer le DataFrame
    df = pd.DataFrame(data)
    
    # Créer le fichier Excel
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Contrats', index=False)
        
        # Formater les colonnes
        worksheet = writer.sheets['Contrats']
        
        # Largeur des colonnes
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(col)
            )
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
    
    output.seek(0)
    
    # Créer la réponse HTTP
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


def export_paiements_to_excel(paiements, filename='paiements.xlsx'):
    """
    Exporte une liste de paiements vers Excel
    """
    data = []
    for paiement in paiements:
        data.append({
            'ID': paiement.id,
            'Professeur': paiement.professeur.user.get_full_name(),
            'Contrat': f"#{paiement.contrat.id}",
            'Module': f"{paiement.contrat.maquette.filiere_sigle}",
            'Statut': paiement.get_status_display(),
            'Montant Brut (FCFA)': float(paiement.montant_brut),
            'Déductions (FCFA)': float(paiement.montant_deductions),
            'Montant Net (FCFA)': float(paiement.montant_net),
            'Mode Paiement': paiement.get_mode_paiement_display() if paiement.mode_paiement else '',
            'Référence': paiement.reference_paiement or '',
            'Date Création': paiement.date_creation.strftime('%d/%m/%Y'),
            'Date Approbation': paiement.date_approbation.strftime('%d/%m/%Y') if paiement.date_approbation else '',
            'Date Paiement': paiement.date_paiement.strftime('%d/%m/%Y') if paiement.date_paiement else '',
            'Créé Par': paiement.cree_par.get_full_name() if paiement.cree_par else '',
            'Approuvé Par': paiement.approuve_par.get_full_name() if paiement.approuve_par else '',
            'Payé Par': paiement.paye_par.get_full_name() if paiement.paye_par else '',
        })
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Paiements', index=False)
        
        worksheet = writer.sheets['Paiements']
        
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).apply(len).max(), len(col))
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
    
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


# ==========================================
# STATISTIQUES ET RAPPORTS
# ==========================================

def generate_statistiques_contrats(date_debut, date_fin):
    """
    Génère des statistiques détaillées sur les contrats
    """
    from .models import Contrat
    from django.db.models import Sum, Avg, Count
    
    contrats = Contrat.objects.filter(
        date_validation__range=[date_debut, date_fin]
    )
    
    stats = {
        'periode': {
            'debut': date_debut,
            'fin': date_fin,
        },
        'general': {
            'nombre_contrats': contrats.count(),
            'nombre_professeurs': contrats.values('professeur').distinct().count(),
            'nombre_classes': contrats.values('classe').distinct().count(),
        },
        'volumes': {
            'total_heures_contractuelles': contrats.aggregate(
                total=Sum('volume_heure_cours') + Sum('volume_heure_td') + Sum('volume_heure_tp')
            )['total'] or 0,
            'moyenne_heures_par_contrat': contrats.aggregate(
                moyenne=Avg('volume_heure_cours') + Avg('volume_heure_td') + Avg('volume_heure_tp')
            )['moyenne'] or 0,
        },
        'financier': {
            'montant_total_contractuel': sum([c.montant_total_contractuel for c in contrats]),
            'montant_total_a_payer': sum([c.calculate_montant_a_payer() for c in contrats]),
        },
        'statuts': {},
        'par_type_enseignement': {},
    }
    
    # Stats par statut
    for status_code, status_label in Contrat.STATUS_CHOICES:
        count = contrats.filter(status=status_code).count()
        if count > 0:
            stats['statuts'][status_label] = count
    
    # Stats par type d'enseignement
    for type_code, type_label in Contrat.TYPE_ENSEIGNEMENT_CHOICES:
        count = contrats.filter(type_enseignement=type_code).count()
        if count > 0:
            stats['par_type_enseignement'][type_label] = count
    
    return stats


def generate_rapport_professeur(professeur, annee_academique):
    """
    Génère un rapport détaillé pour un professeur
    """
    from .models import Contrat
    
    contrats = Contrat.objects.filter(
        professeur=professeur,
        maquette__annee_academique=annee_academique
    )
    
    rapport = {
        'professeur': {
            'nom': professeur.user.get_full_name(),
            'email': professeur.user.email,
            'grade': professeur.grade if hasattr(professeur, 'grade') else '-',
        },
        'annee_academique': annee_academique,
        'nombre_contrats': contrats.count(),
        'contrats': [],
        'totaux': {
            'heures_contractuelles': Decimal('0.00'),
            'heures_effectuees': Decimal('0.00'),
            'montant_contractuel': Decimal('0.00'),
            'montant_paye': Decimal('0.00'),
        }
    }
    
    for contrat in contrats:
        heures_effectuees = contrat.get_heures_effectuees()
        total_effectue = heures_effectuees['cours'] + heures_effectuees['td'] + heures_effectuees['tp']
        
        contrat_info = {
            'id': contrat.id,
            'classe': contrat.classe.nom,
            'module': f"{contrat.maquette.filiere_sigle} - {contrat.maquette.niveau_libelle}",
            'statut': contrat.get_status_display(),
            'heures_contractuelles': float(contrat.volume_total_contractuel),
            'heures_effectuees': float(total_effectue),
            'taux_realisation': float(contrat.taux_realisation),
            'montant_contractuel': float(contrat.montant_total_contractuel),
            'montant_a_payer': float(contrat.calculate_montant_a_payer()),
        }
        
        rapport['contrats'].append(contrat_info)
        
        # Mise à jour des totaux
        rapport['totaux']['heures_contractuelles'] += contrat.volume_total_contractuel
        rapport['totaux']['heures_effectuees'] += total_effectue
        rapport['totaux']['montant_contractuel'] += contrat.montant_total_contractuel
        rapport['totaux']['montant_paye'] += contrat.calculate_montant_a_payer()
    
    return rapport


# ==========================================
# NOTIFICATIONS
# ==========================================

def send_notification_email(user, subject, message, contrat=None):
    """
    Envoie une notification par email
    """
    from django.core.mail import send_mail
    from django.conf import settings
    
    # Construire le message complet
    full_message = f"""
Bonjour {user.get_full_name()},

{message}

"""
    
    if contrat:
        full_message += f"""
Détails du contrat:
- Numéro: #{contrat.id}
- Module: {contrat.maquette.filiere_sigle} - {contrat.maquette.niveau_libelle}
- Classe: {contrat.classe.nom}
- Statut: {contrat.get_status_display()}

Pour plus de détails, connectez-vous à votre espace: {settings.BASE_URL}
"""
    
    full_message += """

Cordialement,
L'équipe IIPEA
"""
    
    try:
        send_mail(
            subject=subject,
            message=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Erreur envoi email: {e}")
        return False


def notify_contrat_validated(contrat):
    """Notifie le professeur de la validation de son contrat"""
    message = f"""
Votre contrat pour le module {contrat.maquette.filiere_sigle} a été validé !

Volume horaire total: {contrat.volume_total_contractuel}h
Montant contractuel: {contrat.montant_total_contractuel:,.0f} FCFA

Le responsable pédagogique vous contactera prochainement pour planifier le démarrage du cours.
"""
    
    return send_notification_email(
        user=contrat.professeur.user,
        subject="Contrat validé - IIPEA",
        message=message,
        contrat=contrat
    )


def notify_cours_started(contrat):
    """Notifie le professeur du démarrage du cours"""
    message = f"""
Votre cours pour le module {contrat.maquette.filiere_sigle} a été démarré.

Type d'enseignement: {contrat.get_type_enseignement_display()}
Date de début: {contrat.date_debut_reelle.strftime('%d/%m/%Y')}

N'oubliez pas de préparer vos supports de cours et votre syllabus, qui devront être déposés à la fin du cours.

Bon enseignement !
"""
    
    return send_notification_email(
        user=contrat.professeur.user,
        subject="Cours démarré - IIPEA",
        message=message,
        contrat=contrat
    )


def notify_documents_required(contrat):
    """Rappel pour charger les documents obligatoires"""
    message = f"""
Rappel: Documents obligatoires manquants !

Votre cours pour le module {contrat.maquette.filiere_sigle} est terminé, mais les documents suivants n'ont pas encore été chargés:

"""
    
    if not contrat.support_cours_uploaded:
        message += "- Support de cours\n"
    if not contrat.syllabus_uploaded:
        message += "- Syllabus du cours\n"
    
    message += """
Ces documents sont obligatoires pour que votre paiement puisse être traité.

Merci de les charger dès que possible dans votre espace.
"""
    
    return send_notification_email(
        user=contrat.professeur.user,
        subject="Documents obligatoires manquants - IIPEA",
        message=message,
        contrat=contrat
    )


def notify_paiement_ready(paiement):
    """Notifie le professeur que son paiement est prêt"""
    message = f"""
Bonne nouvelle ! Votre paiement est prêt.

Contrat: #{paiement.contrat.id}
Module: {paiement.contrat.maquette.filiere_sigle}
Montant net: {paiement.montant_net:,.0f} FCFA

Le paiement sera effectué prochainement par le service comptable.
"""
    
    return send_notification_email(
        user=paiement.professeur.user,
        subject="Paiement en cours de traitement - IIPEA",
        message=message,
        contrat=paiement.contrat
    )


def notify_paiement_done(paiement):
    """Notifie le professeur que son paiement a été effectué"""
    message = f"""
Votre paiement a été effectué avec succès !

Reçu N°: R-{paiement.id:06d}
Contrat: #{paiement.contrat.id}
Module: {paiement.contrat.maquette.filiere_sigle}
Montant net payé: {paiement.montant_net:,.0f} FCFA
Mode de paiement: {paiement.get_mode_paiement_display()}
Date: {paiement.date_paiement.strftime('%d/%m/%Y')}

Vous pouvez télécharger votre reçu depuis votre espace.

Merci pour votre engagement !
"""
    
    return send_notification_email(
        user=paiement.professeur.user,
        subject="Paiement effectué - IIPEA",
        message=message,
        contrat=paiement.contrat
    )






# gestion/utils.py
import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Contrat, ActionLog, Maquette

logger = logging.getLogger(__name__)

def create_contrat_from_module(module, user):
    """
    ⭐ VERSION CORRIGÉE ET DÉBUGUÉE ⭐
    Crée automatiquement un contrat à partir d'un module validé
    """
    with transaction.atomic():
        # Vérifier si un contrat existe déjà pour ce module
        if hasattr(module, 'contrat'):
            logger.info(f"✅ Contrat existe déjà pour le module {module.id}")
            return module.contrat
        
        # Vérifier que le module est bien validé
        if not module.est_valide:
            raise ValidationError(f"Le module {module.nom_module} doit être validé avant de créer un contrat")
        
        try:
            logger.info(f"🔄 Début création contrat pour module: {module.nom_module}")
            
            # Récupérer la maquette associée
            maquette = Maquette.objects.filter(
                classe=module.pre_contrat.classe,
                is_active=True
            ).first()
            
            if not maquette:
                raise ValidationError("Aucune maquette active trouvée pour cette classe")
            
            logger.info(f"✅ Maquette trouvée: {maquette}")
            
            # ⭐ GESTION SÉCURISÉE DE LA RELATION PROFESSEUR
            from Utilisateur.models import Professeur
            
            # Vérifier si l'utilisateur a déjà un profil professeur
            try:
                professeur_instance = module.pre_contrat.professeur.professeur
                logger.info(f"✅ Profil professeur trouvé: {professeur_instance}")
            except Professeur.DoesNotExist:
                # Créer un profil professeur si inexistant
                logger.warning(f"⚠️ Création du profil professeur pour {module.pre_contrat.professeur}")
                professeur_instance = Professeur.objects.create(
                    user=module.pre_contrat.professeur,
                    grade='AUTRE',
                    specialite='Non spécifiée',
                    est_actif=True
                )
                logger.info(f"✅ Profil professeur créé: {professeur_instance}")
            
            # ⭐ CRÉATION DU CONTRAT
            contrat = Contrat.objects.create(
                module_propose=module,
                professeur=professeur_instance,
                classe=module.pre_contrat.classe,
                maquette=maquette,
                volume_heure_cours=module.volume_heure_cours,
                volume_heure_td=module.volume_heure_td,
                taux_horaire_cours=module.taux_horaire_cours,
                taux_horaire_td=module.taux_horaire_td,
                valide_par=user,
                date_validation=timezone.now(),
                status='VALIDATED'
            )
            
            logger.info(f"✅ Contrat #{contrat.id} créé avec succès pour le module {module.nom_module}")
            
            # Log de l'action
            ActionLog.objects.create(
                contrat=contrat,
                action='CREATED',
                user=user,
                details=f"Contrat créé automatiquement depuis le module {module.code_module}"
            )
            
            return contrat
            
        except Exception as e:
            logger.error(f"❌ Erreur création contrat: {str(e)}", exc_info=True)
            raise ValidationError(f"Erreur lors de la création du contrat: {str(e)}")