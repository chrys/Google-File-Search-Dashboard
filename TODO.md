# TODO - Google File Search Dashboard

## In Progress

### Refactor API Response Format
**Objective:** Return bot response and citations as separate JSON fields for better frontend handling and styling

**Tasks:**
- [ ] Update [`src/google_file_search.py`](src/google_file_search.py )
  - [ ] Modify `ask_store_question()` to return tuple `(answer_text, citations_list)` instead of concatenated string
  - [ ] Extract citations from `grounding_metadata` into separate list
  - [ ] Remove duplicates from citations while preserving order

- [ ] Update [`src/app.py`](src/app.py ) Flask endpoint
  - [ ] Change `/api/chat` endpoint to return JSON with separate fields:
    ```json
    {
        "user_message": "question",
        "bot_response": "html_response",
        "citations": ["file1.txt", "file2.pdf"],
        "response_time": 2.37
    }
    ```
  - [ ] Parse response from `ask_store_question()` into separate fields

- [ ] Update [`src/API.py`](src/API.py ) FastAPI endpoint
  - [ ] Modify `/api/chat` endpoint to use new tuple response format
  - [ ] Return same JSON structure as Flask endpoint

- [ ] Update [`templates/chat.html`](templates/chat.html )
  - [ ] Parse JSON response instead of HTML swap
  - [ ] Create separate DOM elements for bot message and citations
  - [ ] Style citations with:
    - [ ] Document icon (📄)
    - [ ] "Sources:" label
    - [ ] List of source files
    - [ ] Distinct visual styling (box/container)
  - [ ] Display response time below citations
  - [ ] Update HTMX form to handle JSON response

**Expected Outcome:**
- Cleaner API contract with separated concerns
- Better frontend styling control over citations
- Improved UX with distinct citation display

**Priority:** Medium
**Estimated Time:** 1-2 hours

---

## Completed ✅

- [x] Add basic authentication to API
- [x] Move API_USERS to .env file
- [x] Add custom prompts per project
- [x] Save prompts to prompts.json
- [x] Implement typing animation while waiting for response
- [x] Add response time tracking
- [x] Create unit tests for google_file_search.py
- [x] Refactor to load prompt when project is selected
- [x] FastAPI implementation

---

## Backlog

### Performance Optimization
- [ ] Implement document caching strategy
- [ ] Add response streaming
- [ ] Test with lighter Gemini model
- [ ] Batch query processing

### UI/UX Improvements
- [ ] Make citations clickable to view source documents
- [ ] Add document preview on citation hover
- [ ] Improve chat message styling
- [ ] Add message search/filtering
- [ ] Add conversation history

### Database Integration
- [ ] Add persistent database for prompts (instead of JSON)
- [ ] Store conversation history
- [ ] Add user management system
- [ ] Add audit logging

### Testing
- [ ] Integration tests for Flask API
- [ ] Integration tests for FastAPI
- [ ] End-to-end tests for chat flow
- [ ] Performance benchmarking suite

### Deployment
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Environment-specific configs
- [ ] Production error monitoring