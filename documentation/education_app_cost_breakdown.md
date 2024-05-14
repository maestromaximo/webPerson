# Cost Analysis for webPerson Django Application

## Introduction
webPerson is a Django application designed to enhance the educational experience by providing features such as lecture transcription, summarization, and interactive conversations with an AI model. This document provides a detailed analysis of the costs associated with using the app, focusing on the flagship GPT-4o model for both semester-long usage and individual chat sessions.

## Semester Cost Estimation

### Breakdown of Features
1. **Lecture Transcription and Summarization**: 
   - **Average word count per lecture**: 6732.67 words
   - **Average tokens per lecture**: 8976.89 tokens
   - **Average word count per summary**: 429.67 words
   - **Average tokens per summary**: 572.89 tokens

2. **Student Transcript**:
   - **Average word count**: 538.2 words
   - **Average tokens**: 717.6 tokens

3. **Student Transcript Summary**:
   - **Average word count**: 147.6 words
   - **Average tokens**: 196.8 tokens

4. **Cross-Prompting**:
   - **Average prompt input**: 5195.4 tokens
   - **Cross-prompting output**: 769.8 tokens

5. **Lesson Fields**:
   - **Total average word count**: 2204.2 words
   - **Total average tokens**: 2939.2 tokens

### Total Token Calculation per Lesson
- **Input tokens**: \( 8976.89 + 717.6 + 5195.4 + 2939.2 \approx 17829.93 \) tokens
- **Output tokens**: \( 572.89 + 196.8 + 769.8 \approx 1539.39 \) tokens

### Cost Calculation
- **Input cost**: \( \frac{17829.93}{1,000,000} \times 5 = \$0.0891 \)
- **Output cost**: \( \frac{1539.39}{1,000,000} \times 15 = \$0.0231 \)
- **Total cost per lesson**: \( \$0.0891 + \$0.0231 = \$0.1122 \)

### Semester Usage
- **Lessons per week**: 11
- **Weeks per semester**: 12
- **Total lessons per semester**: 132
- **Total cost per semester**: \( 132 \times 0.1122 \approx \$15.96 \)
- **Upper bound (10% higher)**: \( 132 \times 0.1330 \approx \$17.55 \)
- **Lower bound (10% lower)**: \( 132 \times 0.1088 \approx \$14.36 \)

## Chat Cost Estimation

### Assumptions
1. **Typing rate**: 40 words per minute
2. **Chat duration**: 10 minutes
3. **Total words typed**: \( 40 \times 10 = 400 \) words
4. **Initial chat content**: Contains the average lesson word count (2204.2 words)

### Token Calculations
- **Initial chat tokens**: \( 2204.2 \div 0.75 \approx 2938.93 \) tokens
- **Chat tokens for 10 minutes**: \( 400 \div 0.75 \approx 533.33 \) tokens
- **Total tokens for initial chat**: \( 2938.93 + 533.33 \approx 3472.27 \) tokens
- **Response tokens per message**: \( 100 \div 0.75 \approx 133.33 \) tokens
- **Total tokens for 10 messages**: \( 3472.27 + (133.33 \times 9) = 4672.27 \) tokens

### Cost Calculation
- **Input tokens**: 4672.27 tokens
- **Output tokens**: \( 4672.27 / 2 = 2336.13 \) tokens
- **Input cost**: \( \frac{4672.27}{1,000,000} \times 5 = \$0.0234 \)
- **Output cost**: \( \frac{2336.13}{1,000,000} \times 15 = \$0.0350 \)
- **Total cost per chat session**: \( \$0.0234 + \$0.0350 = \$0.0584 \)
- **Upper bound (10% higher)**: \( 0.0584 \times 1.1 = \$0.0642 \)
- **Lower bound (10% lower)**: \( 0.0584 \times 0.9 = \$0.0526 \)

## Conclusion
The cost analysis for using the webPerson Django application with the GPT-4o model is summarized as follows:
- **Cost per semester**: 
  - Average: \(\approx \$15.96\)
  - Upper bound: \(\approx \$17.55\)
  - Lower bound: \(\approx \$14.36\)

- **Cost per chat session**: 
  - Average: \(\approx \$0.0584\)
  - Upper bound: \(\approx \$0.0642\)
  - Lower bound: \(\approx \$0.0526\)

These estimates provide a comprehensive understanding of the costs associated with using the webPerson app for both semester-long activities and individual chat sessions. By leveraging the flagship GPT-4o model, users can benefit from advanced AI capabilities while maintaining cost-efficiency.
