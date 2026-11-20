from indic_transliteration import sanscript


print("\nAvailable transliteration schemes:\n")

for name in dir(sanscript):

    if name.isupper():

        print(name)