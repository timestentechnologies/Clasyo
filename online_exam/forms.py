from django import forms
from .models import ExamQuestion, QuestionChoice

class ExamQuestionForm(forms.ModelForm):
    class Meta:
        model = ExamQuestion
        fields = [
            'question_text', 'question_type', 'marks', 'image', 
            'is_required', 'explanation', 'order'
        ]
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 4}),
            'marks': forms.NumberInput(attrs={'step': '0.5', 'min': '0.5'}),
            'image': forms.FileInput(),
            'explanation': forms.Textarea(attrs={'rows': 3}),
            'order': forms.NumberInput(attrs={'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['question_text'].widget.attrs.update({'class': 'form-control rich-editor'})
        self.fields['marks'].widget.attrs.update({'class': 'form-control'})
        self.fields['question_type'].widget.attrs.update({'class': 'form-select'})
        self.fields['image'].widget.attrs.update({'class': 'form-control'})
        self.fields['is_required'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['explanation'].widget.attrs.update({'class': 'form-control'})
        self.fields['order'].widget.attrs.update({'class': 'form-control'})
        
        # Map template field names to model field names
        self.fields['question_text'].label = 'Question Text'
        self.fields['question_type'].label = 'Question Type'
        self.fields['marks'].label = 'Marks'
        self.fields['image'].label = 'Question Image (optional)'
        self.fields['is_required'].label = 'Is Required'
        self.fields['explanation'].label = 'Explanation (optional)'
        self.fields['order'].label = 'Order'

class QuestionChoiceForm(forms.ModelForm):
    class Meta:
        model = QuestionChoice
        fields = ['choice_text', 'is_correct', 'order']
        widgets = {
            'choice_text': forms.TextInput(attrs={'placeholder': 'Enter option text'}),
            'order': forms.NumberInput(attrs={'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['choice_text'].widget.attrs.update({'class': 'form-control'})
        self.fields['is_correct'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['order'].widget.attrs.update({'class': 'form-control'})

# Formset for choices
QuestionChoiceFormSet = forms.modelformset_factory(
    QuestionChoice,
    form=QuestionChoiceForm,
    extra=4,  # Show 4 empty forms by default
    can_delete=True
)
