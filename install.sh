#!/bin/sh

# This is in place of a proper installer.

rsync -av Krisenter.desktop Krisenter.html Krisenter  ~/.local/share/krita/pykrita
rsync -av NextSlide.desktop NextSlide  ~/.local/share/krita/pykrita
rsync -av PrevSlide.desktop PrevSlide  ~/.local/share/krita/pykrita
rsync -av actions/*   ~/.local/share/krita/actions

