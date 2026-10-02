import os
import re
import subprocess
from docx import Document
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from .models import GeneratedDocument

def extraer_etiquetas_docx(archivo_word):
    """Extrae etiquetas con formato {{etiqueta}} de un archivo Word (.docx)."""
    etiquetas = set()
    try:
        doc = Document(archivo_word)
        pattern = re.compile(r"\{\{([^}]+)\}\}")
        
        for p in doc.paragraphs:
            for m in pattern.findall(p.text):
                etiquetas.add(m.strip())
                
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for m in pattern.findall(cell.text):
                        etiquetas.add(m.strip())
    except Exception as e:
        print(f"Error al leer el archivo docx: {e}")
        
    return list(etiquetas)


def rellenar_y_generar_documentos(execution):
    """Procesa todas las plantillas Word reemplazando etiquetas, intenta convertir a PDF y guarda en la BD."""
    template = execution.workflow_template
    document_templates = template.document_templates.all()
    
    if not document_templates.exists():
        return []

    contexto_valores = {}
    
    # Recopilar todos los valores de las respuestas del formulario de manera flexible
    if hasattr(execution, 'form_submission') and execution.form_submission:
        for val in execution.form_submission.values.all():
            texto_respuesta = val.text_value or ""
            
            if val.form_field and val.form_field.placeholder_key:
                contexto_valores[val.form_field.placeholder_key.strip()] = texto_respuesta
            elif val.document_field_mapping and val.document_field_mapping.placeholder_key:
                contexto_valores[val.document_field_mapping.placeholder_key.strip()] = texto_respuesta
            elif val.form_field and val.form_field.label:
                contexto_valores[val.form_field.label.strip()] = texto_respuesta

    archivos_generados = []
    media_root = getattr(settings, 'MEDIA_ROOT', 'media')
    output_dir = os.path.join(media_root, "executions", "generated")
    os.makedirs(output_dir, exist_ok=True)
    
    # Limpiar registros previos de esta ejecución si se vuelve a generar
    GeneratedDocument.objects.filter(workflow_execution=execution).delete()

    for doc_tpl in document_templates:
        try:
            doc = Document(doc_tpl.file.path)
            
            def reemplazar_en_texto(texto_original):
                modificado = texto_original
                pattern = re.compile(r"\{\{([^}]+)\}\}")
                matches = pattern.findall(modificado)
                
                for match in matches:
                    tag_key = match.strip()
                    valor_reemplazo = None
                    for k, v in contexto_valores.items():
                        if k.lower() == tag_key.lower():
                            valor_reemplazo = v
                            break
                    
                    if valor_reemplazo is not None:
                        tag_completo = f"{{{{{match}}}}}"
                        modificado = modificado.replace(tag_completo, str(valor_reemplazo))
                return modificado

            for p in doc.paragraphs:
                nuevo_texto = reemplazar_en_texto(p.text)
                if nuevo_texto != p.text:
                    p.text = nuevo_texto
                        
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        nuevo_texto = reemplazar_en_texto(cell.text)
                        if nuevo_texto != cell.text:
                            cell.text = nuevo_texto

            # Nombre de archivo limpio y corto (ej: NombreDoc_T17.docx)[cite: 20]
            base_filename = os.path.basename(doc_tpl.file.name)
            slug_doc = slugify(doc_tpl.name) or "documento"
            output_filename = f"{slug_doc}_T{execution.id}{os.path.splitext(base_filename)[1]}"
            output_path = os.path.join(output_dir, output_filename)
            
            doc.save(output_path)
            
            pdf_filename = os.path.splitext(output_filename)[0] + ".pdf"
            pdf_path = os.path.join(output_dir, pdf_filename)
            try:
                subprocess.run(
                    ['soffice', '--headless', '--convert-to', 'pdf', output_path, '--outdir', output_dir],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            except Exception:
                pass

            final_filename = pdf_filename if os.path.exists(pdf_path) else output_filename
            final_path = os.path.join(output_dir, final_filename)

            gen_doc = GeneratedDocument.objects.create(
                workflow_execution=execution,
                document_template=doc_tpl,
                name=doc_tpl.name,
                file_path=final_path
            )

            archivos_generados.append({
                'id': gen_doc.id,
                'name': doc_tpl.name,
                'path': final_path,
                'filename': final_filename
            })
        except Exception as e:
            print(f"Error procesando documento {doc_tpl.name}: {e}")

    return archivos_generados