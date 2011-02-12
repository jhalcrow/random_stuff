let dictfn = "/usr/share/dict/words";;
let ngram_len = 3;;

type ngram = EOW | Token of string;;

let rec ngrams_N nlen word =
    if String.length word <= nlen then
        [ Token word ; EOW ]
    else
        Token (String.sub word 0 nlen) :: 
        ngrams_N nlen (String.sub word 1 (String.length word - 1))
;;

let ngrams = ngrams_N ngram_len;;

let sample_multinomial cdf = 
    let r = Random.float 1.0 in
    let rec samplr cdf = 
        match cdf with
              [] -> (raise (Failure "Cannot sample an empty distribution"))
            | (ev, p) :: rest when p > r  -> ev
            | (ev, p) :: rest -> samplr rest
    in
        samplr cdf
;;

let observe_ngrams word hist =
    let grams = ngrams word in
    match grams with
        [ just_me ] ->
        
;;

let assemble_grams grams = 
    match grams with |
        [ gram ] -> 

let generate_word () = 
    let grams = generate_grams () in
    assemble_grams grams
;;
print_string (string_of_list (ngrams (String.lowercase (input_line dictc) ^ "\n")));;
ngrams (String.lowercase (input_line dictc) ^ "\n");;
ngrams (String.lowercase (input_line dictc) ^ "\n");;
