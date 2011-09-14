/* Author: Shawn Nock <nock@nocko.org> */

var imaging = {}; // Global variable container

function update_subject_detail (data) {
    var date = false, out = "";
    $("#subject_name").text(data.name);
    $.each(data.series, 
	   function (i, series) {
	       if (!date) {
		   date = series[1];
		   out += "<p>"+series[1]+":<ol>";
	       }
	       if (!(series[1] == date)) {
		   out += '</ol></p><p>'+series[1]+':<ol>';
		   date = series[1];
	       }
	       out += '<li><a href="javascript:true">'+series[0]+'</a></li>';
	   });
    out += "</ol></p>";
    $("#subject_series").html(out);
    $("#subject_download").html(
	'<form id="download_form"><ul id="dl_options"><li><label>Format:</label>' +
	    '<input type="radio" name="format" value="nii">nii</input>' +
	    '<input type="radio" name="format" value="raw" checked="yes">raw</input></li>' +
	    '<li><label>Compression:</label>' +
	    '<input type="radio" name="compress" value="tar">tar</input>' +
	    '<input type="radio" name="compress" value="tar.bz2" checked="yes">bz2</input>' +
	    '<input type="radio" name="compress" value="zip">zip</input></li>' +
	    '<li><input type="button" name="submit" value="Download"></li></ul>');
    $("#subject_download").find("input:button").click(download);
	     
    $("#subject_series").find("li").click(series_click);

}

function download () {
    var format = $("#download_form input[name=format]:checked").val();
    var compress = $("#download_form input[name=compress]:checked").val();
    if (format != "raw")
	exten = format+"."+compress;
    else
	exten = compress;
    window.open("/download/"+subject+"."+exten);
}

function update_series(series_id) {
    $.getJSON('/api/series/'+series_id, function (data) {
	$("#date").html(data.date);
	$("#program").text(data.program);
    });
}

function series_click () {
    series_id = $(this).text();
    update_series(series_id);
    return false;
}

function clear_subject_detail () {
    $("#subject_name").text(subject);
    $("#subject_id").text("");
    $("#subject_download").text("");
    $("#subject_series").html("<b>Subject data imcomplete in database</b>");
}

function subject_link_click () {
    subject = $(this).text();
    req_obj = $.ajax({url: '/api/subject/'+subject, 
		      dataType: 'json',
		      success: update_subject_detail, 
		      error: clear_subject_detail});
    return false;
}

$().ready(function () {
    $("#projects").find("dd").hide().end().find("dt").click(
	function () {
	    project_id = $(this).next().find("div")[0].id.substr(8);
	    $.getJSON('/api/project/'+project_id, function (data) {
		var out = "";
		$.each(data.subjects, function (i, subject) {
		    out += '<li><a class="subj_link" ';
		    out += 'href="javascript:void true;">'+subject+'</a>';
		});
		$("#project_"+project_id).find("ul").html(out);
		$("a.subj_link").click(subject_link_click);
	    });
	    $("#projects").find("dd:visible").slideUp('fast');
	    $(this).next().slideDown('fast');
	    return false;
	});
    $(".button").hover(
	function () {
	    $(this).addClass("lit")
	},
	function () {
	    $(this).removeClass("lit")
	});
    $("#messages").hide().addClass("info");
});





















