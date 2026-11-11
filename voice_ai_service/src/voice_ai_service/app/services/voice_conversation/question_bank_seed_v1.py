"""Original bilingual starter questions; Reddit links record inspiration, not verified company claims."""

BEHAVIORAL_SOURCE = "https://www.reddit.com/r/cscareerquestions/comments/egx2ng/a_list_of_behavioral_questions_you_should/"
SYSTEM_SOURCE = "https://www.reddit.com/r/leetcode/comments/1j9a8u6/45_system_design_questions_i_curated_for/"
ALGORITHM_SOURCE = "https://www.reddit.com/r/cscareerquestions/comments/73ocdt/should_you_really_tell_you_interviewer_if_youve/"
AMAZON_GUIDE = "https://amazon.jobs/content/en/how-we-hire/tpm-interview-prep"
GOOGLE_GUIDE = "https://research.google.com/pubs/archive/41881.pdf"

# key, format, topic, English and Ukrainian texts, provenance URL (when inspired by a discussion)
QUESTIONS = (
    ("motivation-1", "behavioral", 0, "What motivates you to pursue this role, and what have you done recently to develop the relevant skills?", "Що мотивує вас обрати цю роль і що ви нещодавно зробили для розвитку відповідних навичок?", ""),
    ("motivation-2", "behavioral", 0, "Which part of your field interests you most, and what project or learning experience sparked that interest?", "Яка частина вашого напряму вас найбільше цікавить і який проєкт або досвід навчання пробудив цей інтерес?", ""),
    ("teamwork-1", "behavioral", 1, "Describe a disagreement with a teammate about how to solve a problem. How did you respond and what was the outcome?", "Розкажіть про розбіжність із членом команди щодо вирішення проблеми. Як ви діяли і яким був результат?", BEHAVIORAL_SOURCE),
    ("teamwork-2", "behavioral", 1, "Describe a time you explained a technical decision to someone with a different background. How did you check that you understood each other?", "Опишіть ситуацію, коли ви пояснювали технічне рішення людині з іншим досвідом. Як ви перевірили взаєморозуміння?", ""),
    ("learning-1", "behavioral", 2, "Describe feedback that changed how you approached a project. What did you change and what did you learn?", "Розкажіть про відгук, який змінив ваш підхід до проєкту. Що ви змінили і чого навчилися?", ""),
    ("learning-2", "behavioral", 2, "Tell me about a setback in work, study or a personal project. What did you do next and what would you do differently?", "Розкажіть про невдачу в роботі, навчанні або особистому проєкті. Що ви зробили далі і що змінили б наступного разу?", ""),
    ("duplicates-1", "algorithms", 0, "Given a list of numbers, how would you find the first value that appears twice? Explain correctness and time and space complexity.", "Як знайти перше число, яке повторюється у списку? Поясніть коректність, часову та просторову складність.", ""),
    ("pairs-1", "algorithms", 0, "How would you determine whether a list contains two distinct elements whose sum equals a target? Explain correctness and time and space complexity.", "Як визначити, чи є у списку два різні елементи, сума яких дорівнює заданому числу? Поясніть коректність, часову та просторову складність.", ""),
    ("lookup-1", "algorithms", 1, "How would you compare a hash table and a sorted array for repeated lookups, including construction cost, complexity and memory?", "Як порівняти хеш-таблицю та відсортований масив для повторних пошуків з урахуванням побудови, складності й пам’яті?", ""),
    ("topk-1", "algorithms", 1, "How would you find the k most frequent values in a large list? Compare two approaches and their time and space complexity.", "Як знайти k найчастіших значень у великому списку? Порівняйте два підходи та їхню часову і просторову складність.", ""),
    ("tree-levels-1", "algorithms", 2, "How would you calculate the sum of values at each level of a binary tree? Explain edge cases and time and space complexity.", "Як обчислити суму значень на кожному рівні бінарного дерева? Поясніть крайові випадки, часову та просторову складність.", ALGORITHM_SOURCE),
    ("intervals-1", "algorithms", 2, "How would you merge overlapping intervals? Explain why your approach works, its edge cases and time and space complexity.", "Як об’єднати інтервали, що перетинаються? Поясніть коректність, крайові випадки, часову та просторову складність.", ""),
    ("design-scenario-1", "system-design", 0, "How would you define the workload, reliability needs and budget for a notification service serving 100,000 users?", "Як визначити навантаження, вимоги до надійності та бюджет сервісу сповіщень для 100 000 користувачів?", ""),
    ("design-scenario-2", "system-design", 0, "What workload, latency and cost assumptions would you establish before designing a service for processing user requests?", "Які припущення щодо навантаження, затримки та вартості ви визначили б перед проєктуванням сервісу обробки запитів користувачів?", ""),
    ("design-components-1", "system-design", 1, "How would you design an API rate limiter, including storage, request flow and cost trade-offs?", "Як ви спроєктували б обмежувач частоти API-запитів, зокрема сховище, обробку запитів і компроміси вартості?", SYSTEM_SOURCE),
    ("design-components-2", "system-design", 1, "How would you choose components and storage for a service that ingests and displays operational metrics within a fixed budget?", "Як обрати компоненти й сховище для сервісу збору та відображення операційних метрик у межах фіксованого бюджету?", SYSTEM_SOURCE),
    ("design-change-1", "system-design", 2, "If requests to your service double but the budget stays fixed, what would you change and which trade-offs would you accept?", "Якщо кількість запитів до вашого сервісу подвоїться, а бюджет залишиться незмінним, що ви зміните і які компроміси приймете?", ""),
    ("design-change-2", "system-design", 2, "If a critical dependency becomes unavailable, how would your service degrade and recover without exceeding its budget?", "Як ваш сервіс працюватиме з обмеженою функціональністю та відновиться, якщо критична залежність стане недоступною, не перевищуючи бюджет?", ""),
)

CRITERIA = {
    "behavioral": {
        "en": "Evaluate relevance, clear actions, outcome and reflection; accept study or personal project examples without judging personality.",
        "uk": "Оцінюйте відповідність, зрозумілі дії, результат і висновки; приймайте приклади з навчання чи особистих проєктів без оцінювання особистості.",
    },
    "algorithms": {
        "en": "Evaluate correctness, edge cases, reasoning and justified time and space complexity in Big O; no written code is required.",
        "uk": "Оцінюйте коректність, крайові випадки, аргументацію та обґрунтовану часову й просторову складність Big O; письмовий код не потрібен.",
    },
    "system-design": {
        "en": "Evaluate explicit assumptions, component choices, workload, reliability, budget and reasoned trade-offs relevant to the role.",
        "uk": "Оцінюйте явні припущення, вибір компонентів, навантаження, надійність, бюджет та обґрунтовані компроміси з урахуванням ролі.",
    },
}

# Role-specific anchors complement general questions without inventing a candidate's experience.
ROLE_QUESTIONS = (
    ("design-frontend", "Frontend", "How would you design a dashboard that remains responsive with 100,000 records, and what rendering and budget trade-offs would you consider?", "Як ви спроєктували б панель, що залишається швидкою зі 100 000 записів, і які компроміси рендерингу та бюджету врахували б?"),
    ("design-backend", "Backend", "How would you design a backend service for 100,000 daily requests, and what storage, reliability and budget assumptions would you make?", "Як ви спроєктували б backend-сервіс для 100 000 запитів на день і які припущення щодо сховища, надійності та бюджету зробили б?"),
    ("design-fullstack", "Fullstack", "How would you design a web application for 100,000 users, including client-server communication, data consistency and budget?", "Як ви спроєктували б вебзастосунок для 100 000 користувачів з урахуванням взаємодії клієнта й сервера, узгодженості даних і бюджету?"),
    ("design-devops", "DevOps", "How would you design a deployment pipeline for a service with 100,000 daily users, including rollback, availability and budget?", "Як ви спроєктували б процес розгортання сервісу зі 100 000 користувачів на день з урахуванням відкату, доступності та бюджету?"),
    ("design-mobile", "Mobile", "How would you design data synchronization for a mobile app with 100,000 users, intermittent connectivity and a fixed budget?", "Як ви спроєктували б синхронізацію даних мобільного застосунку для 100 000 користувачів із нестабільним зв’язком та обмеженим бюджетом?"),
    ("design-data", "Data Science", "How would you design a model-serving system for 100,000 predictions per day, including latency, monitoring and inference cost?", "Як ви спроєктували б сервіс моделі для 100 000 прогнозів на день з урахуванням затримки, моніторингу та вартості інференсу?"),
)


def starter_questions():
    """Return immutable migration seed rows; source links are not verified company attributions."""
    rows = []
    for key, focus, topic, english, ukrainian, source in QUESTIONS:
        for language, question in (("en", english), ("uk", ukrainian)):
            reference = source or (AMAZON_GUIDE if focus == "behavioral" else GOOGLE_GUIDE if focus == "algorithms" else SYSTEM_SOURCE)
            provenance = "reddit discussion; original practice wording, company attribution unverified" if "reddit.com" in reference else "official preparation guidance; original practice wording, not an actual company question"
            rows.append({"key": key, "version": 1, "language": language, "focus": focus,
                         "topic_index": topic, "role": "*", "level": "*", "question": question,
                         "criteria": CRITERIA[focus][language], "source_url": reference,
                         "provenance": provenance,
                         "active": True})
    for key, role, english, ukrainian in ROLE_QUESTIONS:
        for language, question in (("en", english), ("uk", ukrainian)):
            rows.append({"key": key, "version": 1, "language": language, "focus": "system-design",
                         "topic_index": 0, "role": role, "level": "*", "question": question,
                         "criteria": CRITERIA["system-design"][language], "source_url": SYSTEM_SOURCE,
                         "provenance": "role-adapted original practice question inspired by public design discussion; company attribution unverified",
                         "active": True})
    return rows
