"""
==============================================
COMMANDE 3: generate_documents_report.py
Emplacement: management/commands/generate_documents_report.py
==============================================
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from utilisateurs.models import Professeur, Section
import json


class Command(BaseCommand):
    help = 'Générer un rapport détaillé sur les documents des professeurs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            default='text',
            choices=['text', 'json', 'html', 'csv'],
            help='Format du rapport (text, json, html, csv)',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Fichier de sortie (affichage console par défaut)',
        )
        parser.add_argument(
            '--section',
            type=str,
            help='Filtrer par section spécifique',
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Rapport détaillé avec toutes les informations',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n📊 Génération du rapport...\n'))
        
        # Construire la requête
        queryset = Professeur.objects.filter(is_active=True)
        
        if options['section']:
            queryset = queryset.filter(sections__nom__icontains=options['section'])
        
        professeurs = queryset.select_related('user').prefetch_related('sections')
        
        # Collecter les statistiques
        stats = self.collect_statistics(professeurs, options['detailed'])
        
        # Générer le rapport selon le format
        if options['format'] == 'json':
            output = self.generate_json_report(stats)
        elif options['format'] == 'html':
            output = self.generate_html_report(stats)
        elif options['format'] == 'csv':
            output = self.generate_csv_report(stats)
        else:
            output = self.generate_text_report(stats, options['detailed'])
        
        # Afficher ou sauvegarder
        if options['output']:
            try:
                with open(options['output'], 'w', encoding='utf-8') as f:
                    f.write(output)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Rapport généré: {options["output"]}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Erreur: {str(e)}')
                )
        else:
            self.stdout.write(output)
    
    def collect_statistics(self, professeurs, detailed=False):
        """Collecter toutes les statistiques"""
        stats = {
            'date_generation': timezone.now(),
            'total': professeurs.count(),
            'complets': 0,
            'incomplets': 0,
            'par_document': {
                'photo': 0,
                'cni': 0,
                'rib': 0,
                'cv': 0,
                'diplome': 0
            },
            'par_section': {},
            'par_grade': {},
            'par_statut': {},
            'manquants': []
        }
        
        for prof in professeurs:
            # Documents complets/incomplets
            if prof.has_complete_documents():
                stats['complets'] += 1
            else:
                stats['incomplets'] += 1
                
                item = {
                    'matricule': prof.matricule,
                    'nom': prof.user.get_full_name(),
                    'email': prof.user.email,
                    'documents_manquants': prof.get_missing_documents()
                }
                
                if detailed:
                    item.update({
                        'telephone': prof.user.telephone,
                        'grade': prof.get_grade_display(),
                        'statut': prof.get_statut_display(),
                        'sections': [s.get_nom_display() for s in prof.sections.all()],
                        'date_creation': prof.created_at.strftime('%d/%m/%Y')
                    })
                
                stats['manquants'].append(item)
            
            # Compter les documents présents
            if prof.photo:
                stats['par_document']['photo'] += 1
            if prof.cni_document:
                stats['par_document']['cni'] += 1
            if prof.rib_document:
                stats['par_document']['rib'] += 1
            if prof.cv_document:
                stats['par_document']['cv'] += 1
            if prof.diplome_document:
                stats['par_document']['diplome'] += 1
            
            # Stats par grade
            grade = prof.get_grade_display()
            stats['par_grade'][grade] = stats['par_grade'].get(grade, 0) + 1
            
            # Stats par statut
            statut = prof.get_statut_display()
            stats['par_statut'][statut] = stats['par_statut'].get(statut, 0) + 1
            
            # Stats par section
            for section in prof.sections.all():
                section_nom = section.get_nom_display()
                if section_nom not in stats['par_section']:
                    stats['par_section'][section_nom] = {
                        'total': 0,
                        'complets': 0,
                        'incomplets': 0
                    }
                stats['par_section'][section_nom]['total'] += 1
                if prof.has_complete_documents():
                    stats['par_section'][section_nom]['complets'] += 1
                else:
                    stats['par_section'][section_nom]['incomplets'] += 1
        
        return stats
    
    def generate_text_report(self, stats, detailed=False):
        """Générer un rapport texte"""
        lines = []
        
        # En-tête
        lines.append('=' * 80)
        lines.append('RAPPORT SUR LES DOCUMENTS DES PROFESSEURS'.center(80))
        lines.append('=' * 80)
        lines.append(f'Généré le: {stats["date_generation"].strftime("%d/%m/%Y à %H:%M")}')
        lines.append('')
        
        # Statistiques globales
        lines.append('📊 STATISTIQUES GLOBALES')
        lines.append('-' * 80)
        total = stats['total']
        lines.append(f'  Total de professeurs actifs: {total}')
        lines.append(
            f'  ✅ Dossiers complets: {stats["complets"]} '
            f'({stats["complets"]/total*100:.1f}%)'
        )
        lines.append(
            f'  ⚠️  Dossiers incomplets: {stats["incomplets"]} '
            f'({stats["incomplets"]/total*100:.1f}%)'
        )
        lines.append('')
        
        # Documents par type
        lines.append('📄 DOCUMENTS PAR TYPE')
        lines.append('-' * 80)
        for doc_type, count in stats['par_document'].items():
            pourcentage = count / total * 100
            bar = '█' * int(pourcentage / 2)
            lines.append(
                f'  {doc_type.upper():10s}: {count:3d}/{total} '
                f'({pourcentage:5.1f}%) {bar}'
            )
        lines.append('')
        
        # Stats par grade
        if stats['par_grade']:
            lines.append('🎓 RÉPARTITION PAR GRADE')
            lines.append('-' * 80)
            for grade, count in sorted(stats['par_grade'].items()):
                lines.append(f'  {grade}: {count}')
            lines.append('')
        
        # Stats par statut
        if stats['par_statut']:
            lines.append('💼 RÉPARTITION PAR STATUT')
            lines.append('-' * 80)
            for statut, count in sorted(stats['par_statut'].items()):
                lines.append(f'  {statut}: {count}')
            lines.append('')
        
        # Stats par section
        if stats['par_section']:
            lines.append('📍 RÉPARTITION PAR SECTION')
            lines.append('-' * 80)
            for section, data in sorted(stats['par_section'].items()):
                lines.append(
                    f'  {section}: {data["total"]} professeurs '
                    f'({data["complets"]} complets, {data["incomplets"]} incomplets)'
                )
            lines.append('')
        
        # Professeurs avec documents manquants
        if stats['manquants']:
            lines.append('⚠️  PROFESSEURS AVEC DOCUMENTS MANQUANTS')
            lines.append('-' * 80)
            for item in stats['manquants']:
                lines.append(f'\n  📋 {item["nom"]} ({item["matricule"]})')
                lines.append(f'     Email: {item["email"]}')
                
                if detailed and 'telephone' in item:
                    lines.append(f'     Téléphone: {item["telephone"] or "Non renseigné"}')
                    lines.append(f'     Grade: {item["grade"]}')
                    lines.append(f'     Statut: {item["statut"]}')
                    lines.append(f'     Sections: {", ".join(item["sections"])}')
                
                docs = ', '.join(item['documents_manquants'])
                lines.append(f'     ⚠️  Manquants: {docs}')
        
        lines.append('')
        lines.append('=' * 80)
        
        return '\n'.join(lines)
    
    def generate_json_report(self, stats):
        """Générer un rapport JSON"""
        # Convertir datetime en string
        stats['date_generation'] = stats['date_generation'].isoformat()
        return json.dumps(stats, indent=2, ensure_ascii=False)
    
    def generate_csv_report(self, stats):
        """Générer un rapport CSV"""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output, delimiter=';')
        
        # En-tête
        writer.writerow([
            'Matricule', 'Nom', 'Email', 'Grade', 'Statut',
            'Photo', 'CNI', 'RIB', 'CV', 'Diplôme',
            'Nb Manquants', 'Documents Manquants'
        ])
        
        # Données
        for item in stats['manquants']:
            missing_docs = item['documents_manquants']
            writer.writerow([
                item['matricule'],
                item['nom'],
                item['email'],
                item.get('grade', ''),
                item.get('statut', ''),
                'Non' if 'Photo de profil' in missing_docs else 'Oui',
                'Non' if 'CNI' in missing_docs else 'Oui',
                'Non' if 'RIB' in missing_docs else 'Oui',
                'Non' if 'CV' in missing_docs else 'Oui',
                'Non' if 'Diplôme' in missing_docs else 'Oui',
                len(missing_docs),
                ', '.join(missing_docs)
            ])
        
        return output.getvalue()
    
    def generate_html_report(self, stats):
        """Générer un rapport HTML"""
        total = stats['total']
        
        html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport Documents Professeurs</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f7fa;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1e3c72;
            border-bottom: 3px solid #2a5298;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #2a5298;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 4px solid #2a5298;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #2a5298;
        }}
        .stat-card h3 {{
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }}
        .stat-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #1e3c72;
        }}
        .stat-card .percentage {{
            color: #666;
            font-size: 14px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #1e3c72;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .warning {{
            color: #ff6b6b;
            font-weight: bold;
        }}
        .success {{
            color: #51cf66;
            font-weight: bold;
        }}
        .progress-bar {{
            background: #e9ecef;
            height: 20px;
            border-radius: 10px;
            overflow: hidden;
            margin: 5px 0;
        }}
        .progress-fill {{
            background: linear-gradient(90deg, #2a5298, #1e3c72);
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Rapport sur les Documents des Professeurs</h1>
        <p style="color: #666; margin-bottom: 30px;">
            Généré le: {stats['date_generation'].strftime("%d/%m/%Y à %H:%M")}
        </p>
        
        <h2>Statistiques Globales</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Professeurs</h3>
                <div class="value">{total}</div>
            </div>
            <div class="stat-card">
                <h3>Dossiers Complets</h3>
                <div class="value success">{stats['complets']}</div>
                <div class="percentage">{stats['complets']/total*100:.1f}%</div>
            </div>
            <div class="stat-card">
                <h3>Dossiers Incomplets</h3>
                <div class="value warning">{stats['incomplets']}</div>
                <div class="percentage">{stats['incomplets']/total*100:.1f}%</div>
            </div>
        </div>
        
        <h2>Documents par Type</h2>
        <table>
            <thead>
                <tr>
                    <th>Type de Document</th>
                    <th>Présents</th>
                    <th>Pourcentage</th>
                    <th>Progression</th>
                </tr>
            </thead>
            <tbody>"""
        
        for doc_type, count in stats['par_document'].items():
            pourcentage = count / total * 100
            html += f"""
                <tr>
                    <td><strong>{doc_type.upper()}</strong></td>
                    <td>{count}/{total}</td>
                    <td>{pourcentage:.1f}%</td>
                    <td>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {pourcentage}%">
                                {pourcentage:.0f}%
                            </div>
                        </div>
                    </td>
                </tr>"""
        
        html += """
            </tbody>
        </table>"""
        
        # Sections
        if stats['par_section']:
            html += """
        <h2>Répartition par Section</h2>
        <table>
            <thead>
                <tr>
                    <th>Section</th>
                    <th>Total</th>
                    <th>Complets</th>
                    <th>Incomplets</th>
                </tr>
            </thead>
            <tbody>"""
            
            for section, data in sorted(stats['par_section'].items()):
                html += f"""
                <tr>
                    <td><strong>{section}</strong></td>
                    <td>{data['total']}</td>
                    <td class="success">{data['complets']}</td>
                    <td class="warning">{data['incomplets']}</td>
                </tr>"""
            
            html += """
            </tbody>
        </table>"""
        
        # Professeurs avec documents manquants
        if stats['manquants']:
            html += """
        <h2>Professeurs avec Documents Manquants</h2>
        <table>
            <thead>
                <tr>
                    <th>Matricule</th>
                    <th>Nom</th>
                    <th>Email</th>
                    <th>Documents Manquants</th>
                </tr>
            </thead>
            <tbody>"""
            
            for item in stats['manquants']:
                docs = ', '.join(item['documents_manquants'])
                html += f"""
                <tr>
                    <td><strong>{item['matricule']}</strong></td>
                    <td>{item['nom']}</td>
                    <td>{item['email']}</td>
                    <td class="warning">{docs}</td>
                </tr>"""
            
            html += """
            </tbody>
        </table>"""
        
        html += """
        <div class="footer">
            <p>Institut IIPEA - Rapport généré automatiquement</p>
        </div>
    </div>
</body>
</html>"""
        
        return html
