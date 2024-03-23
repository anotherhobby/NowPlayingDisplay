-- extend free trail for UI Browser:
-- rm ~/Library/Logs/K6J1GI\(IkG.plist

-- Reference to the target window
tell application "System Events"
	try
		set targetWindow to front window of process "TIDAL"
	on error
		return "{ \"error\": \"Unable to find TIDAL window.\" }"
	end try
end tell

-- extract text elements from the Tidal user interface
tell application "System Events"
	try
		set htmLevel to group 1 of group 1 of group 1 of group 1 of targetWindow		
		set htmlContainer to first UI element of htmLevel
		set containerLevel to group 1 of group 7 of group 2 of group 1 of htmlContainer
		
		set trackTextContainer to UI element 1 of group 1 of group 2 of containerLevel
		set track to description of trackTextContainer
		set track to my replace_quotes(track)
		
		set albumTextContainer to UI element 3 of group 4 of containerLevel
		set album to value of first UI element of albumTextContainer
		set album to my replace_quotes(album)
		
		set artistContainer to group 3 of containerLevel
		set AppleScript's text item delimiters to ", " -- Set delimiter to separate multiple artists with comma
		set artist to description of every UI element of artistContainer as text
		
		set timeContainer to group 3 of group 7 of group 2 of group 1 of htmlContainer
		set timeElapsedContainer to UI element 1 of group 1 of timeContainer
		set timeElapsed to value of timeElapsedContainer
		set totalTimeContainer to UI element 1 of group 2 of timeContainer
		set totalTime to value of totalTimeContainer
		
		set activity to menu item 1 of menu 1 of menu bar item 5 of menu bar 1 of process "TIDAL"
		if name of activity is "Pause" then
			set playerState to "playing"
		else
			set playerState to "paused"
		end if
		
		set previous to enabled of menu item 3 of menu 1 of menu bar item 5 of menu bar 1 of process "TIDAL"
		set next to enabled of menu item 4 of menu 1 of menu bar item 5 of menu bar 1 of process "TIDAL"
		
	on error
		-- determine if the player is stopped or the window isn't responding
		try
			set previous to enabled of menu item 3 of menu 1 of menu bar item 5 of menu bar 1 of process "TIDAL"
			set next to enabled of menu item 4 of menu 1 of menu bar item 5 of menu bar 1 of process "TIDAL"
			if previous is true then
				return "{ \"error\": \"Error retrieving information from TIDAL window.\" }"
			else if next is true then
				return "{ \"error\": \"Error retrieving information from TIDAL window.\" }"
			else
				return "{\"title\": \"\", \"album\": \"\", \"artist\": [\"\"], \"duration\": \"\", \"elapsed\": \"\", \"state\": \"stopped\"}"
			end if
		on error
			return "{ \"error\": \"Error retrieving information from TIDAL window.\" }"
		end try
	end try
end tell



-- Handler to format the artist variable for JSON output
on format_artist(artist)
	set AppleScript's text item delimiters to ", " -- Set delimiter to separate multiple artists
	set artist_list to every text item of artist -- Split the artist string into a list
	-- Replace quotes in each artist name
	set cleaned_artists to {}
	repeat with eachArtist in artist_list
		set end of cleaned_artists to replace_quotes(eachArtist)
	end repeat
	set AppleScript's text item delimiters to ", " -- Set delimiter to separate multiple artists
	set formatted_artists to "[" & (clean_list(cleaned_artists) as text) & "]" -- Join artist names with quotes and square brackets
	set AppleScript's text item delimiters to "" -- Reset text item delimiters
	return formatted_artists
end format_artist

on removeLeadingSpaces(inputText)
	-- Remove one or more leading spaces from the input text
	set textLength to length of inputText
	set startIndex to 1
	repeat while (startIndex � textLength) and ((character startIndex of inputText) = " ")
		set startIndex to startIndex + 1
	end repeat
	set trimmedText to text startIndex thru -1 of inputText
	return trimmedText
end removeLeadingSpaces

-- Handler to replace double quotes with single quotes
on replace_quotes(input_text)
	set AppleScript's text item delimiters to "\""
	set text_items to every text item of input_text
	set AppleScript's text item delimiters to "'"
	set replaced_text to text_items as string
	set AppleScript's text item delimiters to ""
	return replaced_text
end replace_quotes

-- Handler to clean the list and add commas between elements
on clean_list(lst)
	set AppleScript's text item delimiters to "\", \""
	set clean_lst to "\"" & (lst as string) & "\""
	set AppleScript's text item delimiters to ""
	return clean_lst
end clean_list

-- Output JSON to standard out
return "{\"title\": \"" & track & "\", \"album\": \"" & album & "\", \"artist\": " & format_artist(artist) & ", \"duration\": \"" & totalTime & "\", \"elapsed\": \"" & timeElapsed & "\", \"state\": \"" & playerState & "\"}"
title
