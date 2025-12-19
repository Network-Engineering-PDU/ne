

let APP = {

    name: 'App',

    // Low and High Limits
    update_low_and_high_limits: function (elem, model_name, obj_id) {
        let originalText = elem.html();
        $.ajax({
            url: '/update_limits',
            type: 'POST',
            data: {
                'model_name': model_name,
                'obj_id': obj_id,
                'low_limit': $('#inputLowLimit_'+obj_id).val(),
                'high_limit': $('#inputHighLimit_'+obj_id).val(),
            },
            dataType: 'json',
            beforeSend: function (){
                elem.attr('disabled', true).html(SPINNER_SM_DARK);
            },
            success: function(response, textStatus, xhr) {
                elem.attr('disabled', false).html(originalText);
                // alert(response.message);
            },
            error: function (response) {
                elem.attr('disabled', false).html(originalText);
                alert('Error: ' + JSON.stringify(response));
            }
        });
    }
};


$(function() {

});

