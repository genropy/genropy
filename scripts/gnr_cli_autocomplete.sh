_gnr_completions()
{
    if [ ${#COMP_WORDS[@]} -eq 2 ]; then
	COMPREPLY=($(compgen -W "$(GNR_AUTOCOMPLETE=1 gnr)" "${COMP_WORDS[1]}"))
    elif [ ${#COMP_WORDS[@]} -eq 3 ]; then
	COMPREPLY=($(compgen -W "$(GNR_AUTOCOMPLETE=1 gnr ${COMP_WORDS[1]})" "${COMP_WORDS[2]}"))
    else
	COMPREPLY=""
    fi
}

if [ -x "$(command -v gnr)" ]; then
    complete -F _gnr_completions gnr
fi
