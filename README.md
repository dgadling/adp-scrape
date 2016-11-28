# What? Why? #
This is a relatively simple script that download paystubs from the shiny new
ADP website.

This replaces the old version that used `BeautifulSoup` and a bunch of crazy
pattern matching to make things work with something that _mostly_ works like a
REST API client.

## y u no real API? ##
Simple, there isn't one that I can find for mere mortals. There's the ADP
Marketplace but that seems targeted at other HR providers and such.

# How? #
We pretend to be a web browser and make the same kind of calls that the
client-side javascript would make. There's probably some fragility here, but it
turns out to not be much code on this side, so whatever.
