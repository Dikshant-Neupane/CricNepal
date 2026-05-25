from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:8501/')
    page.wait_for_timeout(3000)
    
    # Get all buttons on the page
    buttons = page.query_selector_all('button')
    print("--- BUTTONS ---")
    for i, btn in enumerate(buttons):
        text = btn.text_content() or ''
        tag = btn.evaluate("el => el.tagName")
        attrs = btn.evaluate("el => Array.from(el.attributes).map(a => a.name + '=' + a.value)")
        html = btn.evaluate("el => el.outerHTML")
        print(f"Button {i}: text={repr(text.strip())}, attrs={attrs}")
        print(f"  HTML={html[:200]}")
        
    # Also find any element containing "keyboard"
    print("\n--- KEYBOARD ELEMENTS ---")
    elements = page.query_selector_all('*:has-text("keyboard")')
    for i, el in enumerate(elements):
        text = el.text_content() or ''
        if len(text.strip()) < 50:
            tag = el.evaluate("el => el.tagName")
            attrs = el.evaluate("el => Array.from(el.attributes).map(a => a.name + '=' + a.value)")
            print(f"Element {i}: tag={tag}, text={repr(text.strip())}, attrs={attrs}")
            
    browser.close()
