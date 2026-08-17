import pathlib
diff = pathlib.Path('C:/Users/DafoO/.gemini/antigravity-ide/brain/63dfe7e7-290e-41fe-9c3b-f2cefaa9e5c1/diff.txt').read_text(encoding='utf-8')
walkthrough = pathlib.Path('C:/Users/DafoO/.gemini/antigravity-ide/brain/63dfe7e7-290e-41fe-9c3b-f2cefaa9e5c1/walkthrough.md')
text = walkthrough.read_text(encoding='utf-8')
text += '\n## Source Code Differences\n\n`diff\n' + diff + '\n`\n'
walkthrough.write_text(text, encoding='utf-8')
