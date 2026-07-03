import fitz
doc = fitz.open()
page = doc.new_page()
rect = fitz.Rect(50, 50, 550, 750)
page.insert_textbox(rect, """Chapter 1: The Beginning
This is the first chapter of our test book. It has some interesting English text. Let's see how well it translates to Arabic and converts to audio.

Chapter 2: The Journey
This is the second chapter. The adventure continues. The translator will process this as a separate chapter because of the heading pattern.""")
doc.save("test.pdf")
print("test.pdf created successfully")
