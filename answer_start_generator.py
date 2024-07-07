# answer_start_generator.py
import re
import spacy

# Load the spaCy model
nlp = spacy.load("en_core_web_sm")

def is_acronym(word):
    return word.isupper() and len(word) > 1

def replace_pronouns(text):
    pronoun_map = {
        "my": "your",
        "I": "you",
        "me": "you",
        "mine": "yours"
    }
    tokens = text.split()
    tokens = [pronoun_map.get(token, token) for token in tokens]
    return " ".join(tokens)


def get_subject_and_action(doc):
    subj_text = ""
    action_text = ""
    subj_start_idx = 0
    subj_end_idx = 0

    # Words to exclude from the subject
    exclude_words = {"what", "which", "who", "why", "how", "does", "do", "is", "are", "can", "should"}

    # Identify the main subject phrase (compound nouns, proper nouns, gerunds, etc.)
    for chunk in doc.noun_chunks:
        if chunk.root.dep_ in {"nsubj", "nsubjpass", "csubj", "csubjpass"} and chunk.root.text.lower() not in exclude_words:
            # Extend the subject to include all contiguous descriptive elements
            extended_start = min(token.i for token in chunk if token.dep_ in {"amod", "compound", "det"} or token == chunk.root)
            extended_end = max(token.i for token in chunk if token.dep_ in {"amod", "compound", "det"} or token == chunk.root) + 1
            subj_text = doc[extended_start:extended_end].text
            subj_start_idx = extended_start
            subj_end_idx = extended_end
            break

    # If no noun chunk is found, look for pronouns, adjectives, or acronyms serving as subjects
    if not subj_text:
        for token in doc:
            if (token.dep_ in {"nsubj", "nsubjpass", "csubj", "csubjpass"} and token.text.lower() not in exclude_words) or is_acronym(token.text):
                subj_text = token.text
                subj_start_idx = token.i
                subj_end_idx = token.i + 1
                break

    # Extract the action text after the subject
    action_tokens = [token.text for token in doc[subj_end_idx:] if token.text.lower() not in exclude_words and token.text != '?']
    action_text = " ".join(action_tokens).strip()

    # Replace first-person pronouns with second-person pronouns
    subj_text = replace_pronouns(subj_text)
    action_text = replace_pronouns(action_text)

    return subj_text, action_text

# Function to handle "Is" questions
def handle_is_question(doc):
    # Check if the first token is 'Is' (case insensitive)
    if doc[0].text.lower() == 'is' and doc[-1].text == '?':
        subj_text = ""
        action_text = ""

        # Find the first noun phrase as the subject
        for chunk in doc.noun_chunks:
            subj_text = chunk.text
            subj_start_idx = chunk.start
            subj_end_idx = chunk.end
            break

        # Extract the action text, starting after the subject noun phrase
        action_tokens = [token.text for token in doc[subj_end_idx:] if token.text != '?']

        # Apply acronym logic
        action_tokens = [
            token.upper() if is_acronym(token) else token
            for token in action_tokens
        ]

        action_text = " ".join(action_tokens).strip()

        # Formulate the answer
        answer = f"Yes/no, {subj_text} is/isn't {action_text}"
        return answer.rstrip('?')

# Function to handle "Are" questions
def handle_are_question(question):
    doc = nlp(question)

    if doc[0].text.lower() == 'are' and doc[-1].text == '?':
        subj_text, action_text = get_subject_and_action(doc)
        action_text = action_text.replace("are ", "").strip()
        answer = f"Yes/no,{subj_text} are/aren't {action_text}"
        return answer.rstrip('?')
    return None


# Function to handle auxiliary verb questions
def handle_auxiliary_question(question):
    doc = nlp(question)
    subj_text, action_text = get_subject_and_action(doc)
    action_text = action_text.rstrip('?').strip()

    aux_map = {
        "do":"does/doesn't",
        "can": "can/can't",
        "should": "should/shouldn't",
    }

    action_tokens = action_text.split()
    action_tokens = [token.upper() if is_acronym(token) else token for token in action_tokens]
    action_text = " ".join(action_tokens)

    if doc[0].lemma_ in aux_map:
        aux = aux_map[doc[0].lemma_]
        return f"Yes/no,{subj_text} {aux} {action_text}"

    return None


def handle_does_question(question):
    doc = nlp(question)
    pattern = re.compile(r"Does (\w+(?:\s+\w+)*?)\s+(\w+)\s+(.*)", re.IGNORECASE)
    match = pattern.match(question)

    if match:
        subj_text, action_text = get_subject_and_action(doc)

        # Adjust subject and action if necessary
        if not subj_text:
            subj_text = match.group(1).strip()
            action_text = f"{match.group(2).strip()} {match.group(3).strip()}"
        else:
            action_start = [token.i for token in doc if token.text == match.group(2)][0]
            action_text = " ".join([token.text for token in doc[action_start:]]).strip()

        subj_text = " ".join([token.capitalize() if token.lower() in ["i", "my"] else token for token in subj_text.split()])
        action_tokens = action_text.split()
        action_tokens = [token.upper() if is_acronym(token) else token for token in action_tokens]
        action_text = " ".join(action_tokens).rstrip('?').strip()

        return f"Yes/no, {subj_text} does/doesn't {action_text}"

    return None

# Function to handle "What" questions
def handle_what_question(question):
    def process_action_text(action_text):
        action_tokens = action_text.split()
        action_tokens = [token.upper() if is_acronym(token) else token for token in action_tokens]
        return " ".join(action_tokens).strip().capitalize()

    if "what is" in question.lower():
        action_text = question.replace("What is", "").replace("?", "").strip()
        action_text = process_action_text(action_text)
        return f"{action_text} is"

    elif "what are" in question.lower():
        action_text = question.replace("What are", "").replace("?", "").strip()
        action_text = process_action_text(action_text)
        return f"{action_text} are"

    elif "what does" in question.lower():
        action_text = question.replace("What does", "").replace("?", "").replace("do", "does").strip()
        action_text = process_action_text(action_text)
        return f"{action_text.capitalize()}"

    elif "what causes" in question.lower():
        action_text = question.replace("What causes", "").replace("?", "").strip()
        action_text = process_action_text(action_text)
        return f"{action_text} is caused by"

    elif "what" in question.lower():
        action_text = question.replace("What", "").replace("?", "").replace("are", "").strip()
        action_text = process_action_text(action_text)
        return f"{action_text} are"

    return None

def handle_when_question(question):
    doc = nlp(question)
    subj_text = ""
    action_text = ""

    if doc[0].text.lower() == 'when' and doc[-1].text == '?':
        # Locate the main verb or auxiliary verb following 'when'
        verb_index = None
        for i, token in enumerate(doc):
            if token.pos_ in {"AUX", "VERB"} and i > 0:
                verb_index = i
                break

        # If a verb is found, construct the subject and action text
        if verb_index:
            subj_tokens = [token.text for token in doc[1:verb_index]]
            action_tokens = [token.text for token in doc[verb_index:] if token.text != '?']

            subj_text = " ".join(subj_tokens).strip()
            action_text = " ".join(action_tokens).strip()

            if not any(token.is_upper for token in doc[1:verb_index]):  # Capitalize if not an acronym
                subj_text = subj_text.capitalize()

            # Format action text removing 'did' for past events if needed
            if 'did' in action_text:
                action_text = action_text.replace('did ', '')
                answer = f"{subj_text} {action_text} in"
            else:
                answer = f"{subj_text} {action_text} in"

            return answer.rstrip('?')
    return "None"

# Function to handle "Which" questions
def handle_which_question(question):
    doc = nlp(question)
    if doc[0].text.lower() == 'which' and doc[-1].text == '?':
        which_pattern = r"which (.*)\?$"
        match = re.match(which_pattern, question.lower())
        if match:
            remaining_text = match.group(1).strip()
            subj_tokens = remaining_text.split()
            subj_text = " ".join([token.upper() if is_acronym(token) else token for token in subj_tokens]).strip()
            return f"{subj_text.capitalize()} are"
    return None

def handle_who_question(question):
    doc = nlp(question)
    if doc[0].text.lower() == 'who' and doc[-1].text == '?':
        verb = None
        subject = None

        # Identify the verb and the subject part
        for token in doc:
            if token.dep_ == "ROOT":
                verb = token.text.lower()
            if token.dep_ in {"attr", "nsubj"}:
                subject = " ".join([child.text for child in token.subtree if child.text.lower() not in {"is", "are"}])

        if verb and subject:
            subject_text = " ".join([token.upper() if is_acronym(token) else token for token in subject.split()]).strip()
            if verb == "is":
                return f"{subject_text.capitalize()} is"
            elif verb == "are":
                return f"{subject_text.capitalize()} are"
    return "None"

def handle_how_question(question):
    # Process the question with spaCy
    doc = nlp(question)

    # Lowercase the question for easier matching
    question_lower = question.lower()

    # Handle "How many" questions
    if "how many" in question_lower:
        action_text = question.replace("How many", "").replace("?", "").strip()
        action_text = action_text.replace("are there", "").strip()
        return f"There are many {action_text}"

    # Extract subject and action
    subj_text, action_text = get_subject_and_action(doc)

    # Remove trailing question mark from action_text
    action_text = action_text.rstrip('?').strip()

    # Handle "How is" questions
    if "how is" in question_lower:
        return f"The {subj_text} is {action_text}"

    # Handle "How are" questions
    if "how are" in question_lower:
        if subj_text and action_text:
            subj_tokens = subj_text.split()
            subj_tokens = [token.upper() if is_acronym(token) else token for token in subj_tokens]
            subj_text = " ".join(subj_tokens).strip()
            return f"{subj_text.capitalize()} are {action_text}"
        else:
            action_text = question.replace("How are", "").replace("?", "").strip()
            return f"{action_text.capitalize()} are"

    # Handle "How to" questions
    if "how to" in question_lower:
        # Skip 'how to' and directly take the rest of the sentence as action_text
        action_text = question.replace("How to", "").replace("?", "").strip()
        return f"To {action_text}"

    # Handle "How does" questions
    if "how does" in question_lower:
        subj_tokens = subj_text.split()
        subj_tokens = [token.upper() if is_acronym(token) else token for token in subj_tokens]
        subj_text = " ".join(subj_tokens).strip()
        return f"{subj_text.capitalize()} {action_text}s"

    # Handle "How do" questions
    if "how do" in question_lower:
        subj_tokens = subj_text.split()
        subj_tokens = [token.upper() if is_acronym(token) else token for token in subj_tokens]
        subj_text = " ".join(subj_tokens).strip()
        return f"{subj_text.capitalize()} do {action_text}"

    return None

def handle_why_question(question):
    doc = nlp(question)

    # Extract subject and action using an existing function
    subj_text, action_text = get_subject_and_action(doc)

    # Check if the question starts with 'Why' and ends with '?'
    if doc[0].text.lower() == 'why' and doc[-1].text == '?':
        # Prepare the action text by removing the leading auxiliary or modal, if any
        if action_text.startswith("is ") or action_text.startswith("are ") or action_text.startswith("do ") or action_text.startswith("does "):
            action_text = action_text.split(' ', 1)[1] if len(action_text.split(' ', 1)) > 1 else action_text

        # Create the response
        answer = f"{subj_text.capitalize()} {action_text} because"
        return answer.rstrip(' ').rstrip('?')

    return "None"

def transform_question(question):
    doc = nlp(question)
    subj_text, action_text = get_subject_and_action(doc)

    handlers = [
        (handle_is_question, question),
        (handle_are_question, question),
        (handle_what_question, question),
        (handle_how_question, question),
        (handle_why_question, question),
        (handle_does_question, question),
        (handle_which_question, question),
        (handle_who_question, question),
        (handle_when_question, question),
    ]

    for handler, args in handlers:
        result = handler(args)
        if result:
            return result
    return "No answer found"
