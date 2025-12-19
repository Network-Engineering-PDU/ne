// OUTPUTS VARS
let divOutputsInvalidLicense = $("#divOutputsInvalidLicense");
let tableOutputsData = $("#tableOutputsData");


let OUTPUTS = {

    name: 'Outputs',
    url: `/${LANG_CODE}/outputs/`,

    // Licenses
    get_licenses: function (elem) {
        let originalText = '';
        if (elem !== undefined){
            originalText = elem.html();
        }
        /*
        GET settings/license
        response example:
            {
                "type_id": "A1" or "A2" or "B1" or "B2",
                ...
            }
        */
        $.ajax({
            url: OUTPUTS.url,
            type: 'POST',
            data: {},
            dataType: 'json',
            success: function(response) {
                if (elem !== undefined){
                    elem.attr('disabled', false).html(originalText);
                }
                if (response.result === 'ok'){
                    // Based on license type show or hide output table
                    if (response.type_id === 'A2' || response.type_id === 'B2'){
                        divOutputsInvalidLicense.hide();
                        tableOutputsData.show();
                    }else{
                        divOutputsInvalidLicense.show();
                        tableOutputsData.hide();
                    }
                }else{
                    divOutputsInvalidLicense.show();
                }
            },
            error: function (response) {
                if (elem !== undefined){
                    elem.attr('disabled', false).html(originalText);
                }
                alert('Error: ' + response.message);
            }
        });
    }
};


$(function() {

    // Licenses
    OUTPUTS.get_licenses();

});

