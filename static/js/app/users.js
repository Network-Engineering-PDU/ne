// USERS VARS
// Hosts
let modalUsers = $("#modalUsers");
let btnUserSubmit = $("#btnUserSubmit");


let USERS = {

    name: 'Users',
    url: `/${LANG_CODE}/users/`,

    show_modal_for_users: function (elem, action){
        let trParent = elem.parent().parent();
        let btnText = '';
        let user_id = 0;
        let valueForUsernameField = '';
        let valueForFirstnameField = '';
        let valueForLastnameField = '';
        if (action === 'add'){
            btnText = 'Add User';
        }else if (action === 'edit'){
            btnText = 'Edit User';
            user_id = parseInt(trParent.attr('user_id'));
            valueForUsernameField = trParent.attr('username');
            valueForFirstnameField = trParent.attr('first_name');
            valueForLastnameField = trParent.attr('last_name');
        }else{
            btnText = 'Delete User';
            user_id = parseInt(trParent.attr('user_id'));
            valueForUsernameField = trParent.attr('username');
            valueForFirstnameField = trParent.attr('first_name');
            valueForLastnameField = trParent.attr('last_name');
        }
        // body
        let htmlForBody = ''
        if (action !== 'delete'){
            htmlForBody =
                `<p class="bold textGreen">${btnText}</p>
                 <div class="row">
                    <div class="col-4">
                        <p>Username</p>
                    </div>
                    <div class="col">
                        <div class="input-group mb-3">
                            <input id="inputUsername" type="text" class="form-control" value="${valueForUsernameField}" />
                        </div>
                    </div>
                 </div>
                 <div class="row">
                    <div class="col-4">
                        <p>Firstname</p>
                    </div>
                    <div class="col">
                        <div class="input-group mb-3">
                            <input id="inputUserFirstName" type="text" class="form-control" value="${valueForFirstnameField}" />
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-4">
                        <p>Lastname</p>
                    </div>
                    <div class="col">
                        <div class="input-group mb-3">
                            <input id="inputUserLastName" type="text" class="form-control" value="${valueForLastnameField}" />
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-4">
                        <p>Password</p>
                    </div>
                    <div class="col">
                        <div class="input-group mb-3">
                            <input id="inputUserPassword" type="password" class="form-control" value="" />
                        </div>
                    </div>
                </div>`;
        }else{
            htmlForBody =
                `<div class="iconWarn"></div>
                <p class="bold text-center">
                    ARE YOU SURE YOU WANT TO DELETE THIS USER ?
                </p>
                <p>(This action can not be undone).</p>
                <div class="d-flex justify-content-start bd-highlight">
                    <div class="p-2 bd-highlight">
                        <span class="fw-bold">Username:</span> ${valueForUsernameField}
                    </div>
                </div>
                <div class="d-flex justify-content-start bd-highlight">
                    <div class="p-2 bd-highlight">
                        <span class="fw-bold">Firstname:</span> ${valueForFirstnameField}
                    </div>
                </div>
                <div class="d-flex justify-content-start bd-highlight">
                    <div class="p-2 bd-highlight">
                        <span class="fw-bold">Lastname:</span> ${valueForLastnameField}
                    </div>
                </div>`
        }
        // modal body dynamic content
        modalUsers.find('.modal-body').html(htmlForBody);
        // submit button
        btnUserSubmit.attr('action', action).attr('user_id', user_id).html(btnText);
        // show modal
        modalUsers.modal({
            "backdrop":"static",
            "width": "300px"
        }).modal("show");
    },

    submit_user: function (elem){
        let originalText = elem.html();
        let action = elem.attr('action');
        let user_id = elem.attr('user_id');
        let inputUserFirstName = $('#inputUserFirstName');
        let inputUserLastName = $('#inputUserLastName');
        let inputUsername = $('#inputUsername');
        let inputUserPassword = $('#inputUserPassword');
        let username = inputUsername.val();
        let first_name = inputUserFirstName.val();
        let last_name = inputUserLastName.val();
        let password = inputUserPassword.val();

        // validations
        if (action !== 'delete'){
            if (!username || username === '' || username === undefined){
                inputUsername.addClass('borderRed');
                return false;
            }else{
                inputUsername.removeClass('borderRed');
            }
            if (!first_name || first_name === '' || first_name === undefined){
                inputUserFirstName.addClass('borderRed');
                return false;
            }else{
                inputUserFirstName.removeClass('borderRed');
            }
            if (!last_name || last_name === '' || last_name === undefined){
                inputUserLastName.addClass('borderRed');
                return false;
            }else{
                inputUserLastName.removeClass('borderRed');
            }
            if (!password || password === '' || password === undefined){
                inputUserPassword.addClass('borderRed');
                return false;
            }else{
                inputUserPassword.removeClass('borderRed');
            }
        }
        $.ajax({
            url: USERS.url,
            type: 'POST',
            data: {
                'action': action,
                'id': user_id,
                'first_name': first_name,
                'last_name': last_name,
                'username': username,
                'password': password,
            },
            dataType: 'json',
            beforeSend: function (){
                elem.attr('disabled', true).html(SPINNER_SM_DARK);
            },
            success: function(response) {
                elem.attr('disabled', false).html(originalText);
                if (response.result === 'ok'){
                    modalUsers.modal('hide');
                    setTimeout(function (){
                        location.reload();
                    }, 500);
                }
                alert(response.message);
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

