 open Printf
 

    let dictf = open_in "/usr/share/dict/words" in
    let rec chan_to_list chan = 
        try
            let line = input_line dictf in 
        with
            End_of_file -> []
        line :: chan_to_list
     chan_to_list dictf    
    ;;