from django.core.management.base import BaseCommand
from education.models import Template, Prompt

class Command(BaseCommand):
    help = 'Create default template and prompts for study guide generation'

    def handle(self, *args, **kwargs):
        template_name = "Default Study Guide Template"
        template_description = "A template that guides through a thought process to create a study guide."
        
        # Create the template
        template, created = Template.objects.get_or_create(name=template_name, defaults={'description': template_description})
        
        if created:
            self.stdout.write(self.style.SUCCESS('Successfully created template: %s' % template_name))
        else:
            self.stdout.write(self.style.WARNING('Template already exists: %s' % template_name))
        
        # Define prompts
        prompts = [
            {
                'order': 1,
                'prompt_text': "Hi, I need you to create a study sheet, a well-thought and logical study sheet for this class. The class name is {class_name}. But I want you to not write the study sheet right away. I need you to only follow the steps of Thinking, Planning, Rehearsing, Creating, Checking back, Planning for Fixes, and only then actually creating the study sheet. I want you to stick to specific steps. First, I want you to plan what a great study guide would have for a midterm for this class. Be sure to include everything that's necessary, but before planning out just think logically what are the things that should be included."
            },
            {
                'order': 2,
                'prompt_text': "Here are the lecture summaries for the lectures that are going to be covered on the midterm:\n\n{lectures}\n\nBased on the information you provided in the previous step, plan how you would make the study guide. Don't write it in full, just plan a thoughtful setup of how you would structure it. What would you put and where? What are things that you need to place for the study guide based on the information from these lesson summaries."
            },
            {
                'order': 3,
                'prompt_text': "Given the information you extracted and planned, now create the study guide based on that."
            },
            {
                'order': 4,
                'prompt_text': "Please look back at the study guide and see if there's anything you would like to change or add. Any improvements that you see, if you don't see any don't worry, but I need you to rewrite the study guide one more time with any improvements if you have any."
            },
            {
                'order': 5,
                'prompt_text': "Now, please rewrite the entire study guide in LaTeX format. Only answer with the LaTeX code, no pre-messages or additional text.\n\n**Restrictions:**\n1. Ensure that the LaTeX document starts with \\documentclass{article} and includes the necessary packages such as amsmath, amsfonts, and geometry.\n2. Use the \\begin{document} and \\end{document} tags to enclose the document content.\n3. Ensure all sections, subsections, and environments are properly closed.\n4. Use \\section, \\subsection, and \\subsubsection commands appropriately for sections and subsections.\n5. Ensure all LaTeX commands are correctly spelled and formatted.\n6. Do not include any commands or environments that are not supported by basic LaTeX.\n7. Include the \\maketitle command after defining the title, author, and date.\n8. Ensure all mathematical expressions are enclosed within \\[ \\] or \\( \\) for display and inline math modes respectively.\n9. Ensure any tables or figures are properly formatted and enclosed within the appropriate environments.\n10. Avoid using any non-standard or unsupported LaTeX packages."
            }
        ]

        for prompt_data in prompts:
            Prompt.objects.get_or_create(template=template, order=prompt_data['order'], defaults={'prompt_text': prompt_data['prompt_text']})

        self.stdout.write(self.style.SUCCESS('Successfully created prompts for the template'))
