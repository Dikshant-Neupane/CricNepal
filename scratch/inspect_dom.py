from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:8501/')
    page.wait_for_timeout(3000)
    
    # Find any elements containing 'keyboard'
    elements = page.query_selector_all('*')
    for el in elements:
        text = el.text_content() or ''
        if 'keyboard' in text and len(text) < 100:
            tag = el.evaluate("el => el.tagName")
            attrs = el.evaluate("el => Array.from(el.attributes).map(a => a.name + '=' + a.value)")
            print(f"Tag: {tag}, Attrs: {attrs}, Text: {text.strip()}")
    browser.close()
