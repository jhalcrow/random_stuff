function random_color_gen(colorlist) {
    return (function() {
        index = Math.floor(Math.random() * colorlist.length);
        return colorlist[index]
    });
}

function draw_mondrian(canvas, budget) {
    canvas.width = canvas.width; // Reset the canvas
    var ctx = canvas.getContext("2d");
    ctx.strokeStyle = "rgb(0,0,0)";
    ctx.lineWidth = 3.0;
    colors = random_color_gen(['red','blue','yellow', 'white', 'black', 'white', 'white']);
    draw_mondrian_inner(ctx, budget, [0, 1], [0, 1], colors);    
}

function assertOk(pivot, iv) {
    if(pivot < iv[0] || pivot > iv[1]) {
        alert("Invalid pivot! " + iv + " " + pivot);
    }
}

function draw_mondrian_inner(ctx, budget, x, y, colorfun) {
    ctx.fillStyle = colorfun()
    
    var width = x[1] - x[0];
    var height = y[1] - y[0];
    
    var cost = sample_exp(width + height);
    //debug_log('Cost: ' + cost)
    if(cost < budget) {
        var remaining = budget - cost;
        var cut = Math.random() * (width + height);
        
        if(cut < width) {
            var pivot = cut + x[0];
            assertOk(pivot, x);
            draw_mondrian_inner(ctx, remaining, [x[0], pivot], y, colorfun);
            draw_mondrian_inner(ctx, remaining, [pivot, x[1]], y, colorfun);
        } else {
            var pivot = cut - width + y[0];
            assertOk(pivot, y);
            draw_mondrian_inner(ctx, remaining, x, [y[0], pivot], colorfun);
            draw_mondrian_inner(ctx, remaining, x, [pivot, y[1]], colorfun);
        }
    } else {
        var x0 = x[0] * ctx.canvas.width;
        var y0 = y[0] * ctx.canvas.height;
        var cwidth = width * ctx.canvas.width;
        var cheight = height * ctx.canvas.height;
        ctx.strokeRect(x0, y0, cwidth, cheight);
        ctx.fillRect(x0, y0, cwidth, cheight);
    }
}

function sample_exp(lambda) {
    r = Math.random();
    return -1.0 * Math.log(1 - r) / lambda
}

