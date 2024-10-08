#!/bin/bash
API_ROOT=https://google-webfonts-helper.herokuapp.com/api
FONT_ID=barlow-condensed
FONT_FILENAME_REGULAR=regular.woff
FONT_FILENAME_BOLD=bold.woff

FONT_FILENAME_REGULAR_TTF=barlow-condensed.regular.ttf
FONT_FILENAME_BOLD_TTF=barlow-condensed.bold.ttf

echo Fetching variants info for id "$FONT_ID"
ALL_FONTS=$(curl -s $API_ROOT/fonts/$FONT_ID)

REGULAR=$(echo "$ALL_FONTS" | jq '.variants[] | select(.id == "regular") | .woff')
BOLD=$(echo "$ALL_FONTS" | jq '.variants[] | select(.id == "700") | .woff')

REGULAR_TTF=$(echo "$ALL_FONTS" | jq '.variants[] | select(.id == "regular") | .ttf')
BOLD_TTF=$(echo "$ALL_FONTS" | jq '.variants[] | select(.id == "700") | .ttf')


FONT_FAMILY=$(echo "$ALL_FONTS" | jq '.family')

if [[ -n "$REGULAR" && -n "$BOLD" ]]
then
  echo Saving a regular and bold variants of the font $FONT_FAMILY
  echo $REGULAR | xargs curl -s -o eInk-weather-display/fonts/$FONT_FILENAME_REGULAR
  echo $BOLD | xargs curl -s -o eInk-weather-display/fonts/$FONT_FILENAME_BOLD
  echo $REGULAR_TTF | xargs curl -s -o eInk-weather-display/fonts/$FONT_FILENAME_REGULAR_TTF
  echo $BOLD_TTF | xargs curl -s -o eInk-weather-display/fonts/$FONT_FILENAME_BOLD_TTF
  echo cp eInk-weather-display/fonts/*ttf ~/.local/share/fonts/
  echo fc-cache -f -v
  echo Fonts downloaded succesfully
else
  echo Could not find all font variants!
  echo Regular=$REGULAR
  echo Bold=$BOLD
  echo Regular=$REGULAR_TTF
  echo Bold=$BOLD_TTF
fi


