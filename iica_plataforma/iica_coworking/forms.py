from django.forms import ModelForm, Textarea, Form,FileField
# from crispy_forms.helper import FormHelper
# from crispy_forms.layout import Submit
from iica_coworking.models import Slide
from django import forms
from colorfield.widgets import ColorWidget

# class FileUploadForm(forms.Form):
#     file = forms.FileField(label='Selecciona un archivo')
#     name = forms.CharField(label='Nombre de slide')
#     decription = forms.CharField(label='Descripcion del slide')

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.form_id = 'file-upload-form'
#         self.helper.form_method = 'post'
#         self.helper.form_class = 'form-horizontal'
#         self.helper.add_input(Submit('submit', 'Subir'))
class UploadFileForm(forms.Form):
    name = forms.CharField(max_length=100, label='Nombre')
    description = forms.CharField(widget=forms.Textarea, label='Descripción')



class SlideForm(forms.ModelForm):
    auto_color = forms.BooleanField(
        required=False,
        label='Revisar imagen y seleccionar color de fondo automáticamente',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    color = forms.CharField(
        required=False,
        label='Color de fondo (se usará si no se selecciona la opción anterior)',
        widget=ColorWidget(attrs={'class': 'form-control'}),
        initial='#ffffff'
    )

    class Meta:
        model = Slide
        fields = ['name', 'description', 'auto_color', 'color']
        labels = {
            'name': 'Titulo',
            'description': 'Descripción',
            'color': 'Color',
        }

    def __init__(self, *args, **kwargs):
        super(SlideForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['class'] = 'form-control'
        self.fields['name'].widget.attrs['placeholder'] = 'Titulo del slide'
        self.fields['description'].widget.attrs['class'] = 'form-control'
        self.fields['description'].widget.attrs['placeholder'] = 'Descripción del slide'
        self.fields['color'].widget.attrs['class'] = 'form-control'
        self.fields['color'].widget.attrs['placeholder'] = 'Color del slide (opcional)'

    def clean(self):
        cleaned_data = super().clean()
        auto_color = cleaned_data.get("auto_color")
        color = cleaned_data.get("color")

        if auto_color:
            cleaned_data['color'] = None

        return cleaned_data