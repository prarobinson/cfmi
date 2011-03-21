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
    $("gen_inv").click(function() { 
            var month =	$("#ui-datepicker-div .ui-datepicker-month :selected").val();
            var year = $("#ui-datepicker-div .ui-datepicker-year :selected").val();
	    month = parseInt(month)+1;
	    $.getJSON('/api/batch/gen_invoices', {
		'year': year, 'month': month}, function (data) {
		    console.warn(data);
		})
    });
})

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

/* Not sure that we need this functionality, leaving it in 
   so I don't have to rewrite it incase I am wrong

function update_project_browser (link, year, month) {
    pi_id = link.id;
    console.debug(year, month);
    $.getJSON('/api/activePI/'+pi_id, {
	'year': year, 'month': month}, function (data) {
	    var out = '<ul>';
	    $.each(data.object_list, function (i, project) {
		out += '<li><a href="#" id="'+project.id+'">'
		out += project.shortname+'</a></li>'
	    });
	    out += '<li><a href="/'+data.piuname+'/'+year+'/'+month+'/">'
	    out += 'All Projects</a></li></ul>'
	    $("#project_selector").html(out);
	    $("#project_selector").find("li").addClass("packed_2_col");
	    $("#project_selector").find("a").click(function () {
		
	    });
	});
}

*/