from django.core.management.base import BaseCommand
from education.models import Prompt

PROMPTS = [
    # Insight-focused prompts
    {
        "title": "Comparison of Key Concepts",
        "prompt": "Identify and compare key concepts mentioned in both the lecture transcript and the student's summary...",
        "description": "Compares key concepts from lecture and student summaries for insight into understanding gaps.",
        "category": "Insight",
    },
    {
        "title": "Understanding Gaps",
        "prompt": "Based on the lecture transcript and the student's summary, identify any topics or themes the student may have misunderstood...",
        "description": "Identifies gaps in understanding between lecture content and student summaries.",
        "category": "Insight",
    },
    {
        "title": "Strengths in Student's Understanding",
        "prompt": "Analyze the student's summary to identify strengths in their understanding of the lecture...",
        "description": "Highlights areas of strong comprehension in student summaries.",
        "category": "Insight",
    },
    
    # Technical detail prompts
    {
        "title": "Direct Concept Comparison",
        "prompt": "Directly compare the concepts and topics covered in the lecture transcript with those mentioned in the student's summary...",
        "description": "Direct comparison of lecture and student summary concepts for accuracy and completeness.",
        "category": "Technical",
    },
    {
        "title": "Accuracy of Information",
        "prompt": "Evaluate the accuracy of the information in the student's summary compared to the lecture transcript...",
        "description": "Assesses accuracy of student summaries against lecture content.",
        "category": "Technical",
    },
    {
        "title": "Detail Level Comparison",
        "prompt": "Compare the level of detail between the lecture's content and the student's summary...",
        "description": "Compares detail levels to identify oversimplifications or appropriate depth in student summaries.",
        "category": "Technical",
    },
    
    # Creative synthesis prompts
    {
        "title": "Creative Synthesis of Ideas",
        "prompt": "Encourage a creative synthesis of the ideas discussed in the transcript(s)...",
        "description": "Prompts creative application and synthesis of lecture materials.",
        "category": "Creative",
    },
    
    # Real-world applications
    {
        "title": "Real-World Applications",
        "prompt": "Identify and describe real-world applications or examples of the concepts discussed in the transcript(s)...",
        "description": "Links lecture concepts to their real-world applications.",
        "category": "Other",
    },
    {
        "title": "Interdisciplinary Connections",
        "prompt": "Examine the transcript(s) for connections to other disciplines or fields of study...",
        "description": "Identifies interdisciplinary links and their implications for broader understanding.",
        "category": "Other",
    },
    {
    "title": "Summarize Transcripts",
    "prompt": "Given the following transcript from a {class} class, craft a summary that captures the main purpose and key points discussed. Ensure the summary is coherent, concise, and reflective of the essential themes, making it suitable for students who may not have attended the lecture. Consider the specific context of the {class} subject to maintain the accuracy and relevance of the summary.\n\nTranscript:\n\"{transcript}\"",
    "description": "Generates a focused summary of a transcript, preserving its main purpose and context, tailored to a specific class.",
    "category": "Technical",
}

]

class Command(BaseCommand):
    help = 'Initializes the database with predefined prompts'

    def handle(self, *args, **options):
        for prompt_data in PROMPTS:
            obj, created = Prompt.objects.update_or_create(
                title=prompt_data["title"],
                defaults={
                    'prompt': prompt_data["prompt"],
                    'description': prompt_data["description"],
                    'category': prompt_data["category"],
                    'active': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created prompt: {obj.title}'))
            else:
                self.stdout.write(self.style.WARNING(f'Updated prompt: {obj.title}'))
