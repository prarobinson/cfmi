/* Author: Shawn Nock <nock@nocko.org> */

$().ready(function () {
    $("#browser").accordion({autoHeight: false});
    $("#datepicker").datepicker({
	changeMonth: true,
	changeYear: true,
	showButtonPanel: true,
        dateFormat: 'MM yy',
        onClose: function(dateText, inst) { 
            var month =	$("#ui-datepicker-div .ui-datepicker-month :selected").val();
            var year = $("#ui-datepicker-div .ui-datepicker-year :selected").val();
            $(this).datepicker('setDate', new Date(year, month, 1));
	    month = parseInt(month)+1
	    update_pi_browser(year, month);
	    $("#browser").accordion({active: 1});
	}});
    $("#invdatepicker").datepicker({
	changeMonth: true,
	changeYear: true,
	showButtonPanel: true,
        dateFormat: 'MM yy',
	onClose: function(dateText, inst) {
	    var month =	$("#ui-datepicker-div .ui-datepicker-month :selected").val();
            var year = $("#ui-datepicker-div .ui-datepicker-year :selected").val();
            $(this).datepicker('setDate', new Date(year, month, 1));
	}});
    $("#gen_inv").click(function() { 
            var month =	$("#ui-datepicker-div .ui-datepicker-month :selected").val();
            var year = $("#ui-datepicker-div .ui-datepicker-year :selected").val();
	    month = parseInt(month)+1;
	    $.getJSON('/api/batch/gen_invoices', {
		'year': year, 'month': month}, function (data) {
		    console.warn(data);
		})
    });
    $("#gen_report").click(function() {
	var month = $("#ui-datepicker-div .ui-datepicker-month :selected").val();
        var year = $("#ui-datepicker-div .ui-datepicker-year :selected").val();
	month = parseInt(month)+1;
	var url = "/batch/report?year="+encodeURIComponent(year);
	url += "&month="+encodeURIComponent(month);
	window.location.href = url;
    });
	
    $(".inv_link").click(function () {
	var inv_id = /\/([0-9]+)\//.exec(this.href)[1];
	if (this.href.match(/delete/)) {
	    ajax_delete('invoice', inv_id, function () {
		$("#"+inv_id).hide();
	    });
	    return false;
	}
	if (this.href.match(/paid/)) {
	    ajax_update('invoice', inv_id, {reconciled: true}, function () {
		$("#"+inv_id).hide();
	    });
	    return false;
	}
    });
    $("#gen_stat").click(function () {
	$.getJSON('/api/batch/update_stats', function () {
	    console.log("Tried to clear cache");
	})
    });
});

function update_pi_browser (year, month) {
    $.getJSON('/api/activePI', {
	'year': year, 'month': month}, function (data) {
	    var out = '<ul>';
	    console.debug(year, month)
	    $.each(data.object_list, function (i, pi) {
		out += '<li><a href="/'+pi.username+'/'+year+'/'+month+'/">'
		out += pi.name+'</a></li>'
	    });
	    out += "</li>"
	    $("#pi_selector").html(out);
	    $("#pi_selector").find("li").addClass("packed_4_col");
	});
}

function ajax_fetch(type, id, context, callback) {
    var url = '/api/db/'+type+'/'+id;
    $.ajax({url: url, success: callback, context: context});
}

function ajax_create(type, object, context, callback) {
    var url = '/api/db/'+type;
    $.ajax({url: url,
	    data: JSON.stringify(object),
	    type: "POST",
	    contentType: 'application/json',
	    success: callback
	   });
}

function ajax_update(type, id, object, callback) {
    var url = '/api/db/'+type+'/'+id;
    $.ajax({url: url,
	    data: JSON.stringify(object),
	    type: "PUT",
	    contentType: 'application/json',
	    success: callback
	   });
}

function ajax_delete(type, id, callback) {
    var url = '/api/db/'+type+'/'+id;
    $.ajax({url: url,
	    type: "DELETE",
	    success: callback
	   });
}


// function Problem (id) {
//     this.type = 'problem';
//     this._persistant = false;
//     this.id = id;
//     if (this.id) {
// 	ajax_fetch(this.type, this.id, this, function(data) {
// 	    console.warn("In update callback");
// 	    console.warn(data)
// 	    this.session_id = data.session_id;
// 	    this.description = data.description;
// 	    this.duration = data.duration;
// 	    this._persistant = true;
// 	});
//     }

//     this.obj = function () {
// 	return {
// 		description: this.description,
// 		duration: this.duration,
// 		session_id: this.session_id
// 	       }
//     }

//     this.push = function () {
// 	if (this._persistant == true) 
// 	{
// 	    ajax_update(this.type, this.id, this.obj(), this, function (data) { 
// 		console.warn("Updated Problem: "+data.id);
// 		this._persistant = true;
// 	    })
// 	}
// 	else
// 	{
// 	    ajax_create(this.type, this.obj(), this, function (data) { 
// 		console.warn("Created Problem: "+data.id);
// 		this.id = data.id
// 		this._persistant = true;
// 	    })
// 	}
//     }	    
//     this.rm = function () {
// 	console.warn(this);
// 	ajax_delete(this.type, this.id, this, function (data) { 
// 	    console.warn("Deleted Problem: " +this.id);
// 	    this._persistant = false;
// 	});
//     }
//     this.pull = function () {
// 	ajax_fetch(this.type, this.id, this, this._update);
//     }
// }






















