/** @odoo-module **/
import ajax from "web.ajax";

const encoder = new TextEncoder();

const CHAR_MAP = {
    "ñ": "n",
    "Ñ": "N",
    "á": "a",
    "é": "e",
    "í": "i",
    "ó": "o",
    "ú": "u",
    "Á": "A",
    "É": "E",
    "Í": "I",
    "Ó": "O",
    "Ú": "U",
    "ä": "a",
    "ë": "e",
    "ï": "i",
    "ö": "o",
    "ü": "u",
    "Ä": "A",
    "Ë": "E",
    "Ï": "I",
    "Ö": "O",
    "Ü": "U",
};

const EXPRESSION = new RegExp(`[${Object.keys(CHAR_MAP).join("")}]`, "g");

export function sanitize(string) {
    return string.replace(EXPRESSION, (char) => CHAR_MAP[char]);
}

export function toBytes(command) {
    const commands = Array.from(encoder.encode(command));

    commands.push(3);
    commands.push(commands.reduce((prev, curr) => prev ^ curr, 0));
    commands.unshift(2);

    return new Uint8Array(commands);
}

export const PrintingMixin = (Parent) => class extends Parent {
    timeout = null;
    printerCommands = [];
    printing = false;
    read_s2 = false;
    read_Z = false;
    writer = false;
    reader = false;
    verificar_desconexion = false;

    get reader() {
        return this.port?.readable?.getReader();
    }

    get port() {
        return this.env.pos.serialPort;
    }

    set port(serialPort) {
        this.env.pos.serialPort = serialPort;
    }

    async setPort() {
        try {
            const port = await navigator.serial.requestPort();
            if (this.port) {
                await this.port.close();
            }
            await port.open({
                baudRate: this.env.pos.config.x_fiscal_command_baudrate || 9600,
                parity: "even",
                dataBits: 8,
                stopBits: 1,
                bufferSize: 256,
            });
            this.port = port;
            if (!this.verificar_desconexion) {
                this.verificar_desconexion = true;
                navigator.serial.addEventListener('disconnect', e => {
                    console.log("Puerto Desconectado");
                    this.port = this.printing = this.writer = false;
                });
            }
    
            return true;
        } catch (error) {
            console.error(error);
            alert("Hubo un error al tratar de abrir el puerto");
            this.port = this.printing = this.writer = false;
            return false;
        }
    }
    async escribe_leer(command, is_linea) {
        if(!this.port) return false;
        var comando_cod = toBytes(command);
        console.log("Escribiendo comando: ");
        console.log(command)
        console.log("Comando codificado: ");
        console.log(comando_cod);
        this.writer = this.port.writable.getWriter();
        var signals_to_send = { dataTerminalReady: true };
        if(this.env.pos.config.connection_type === "usb_serial"){
            signals_to_send = { requestToSend: true };
        }
        await this.port.setSignals(signals_to_send);
        var signals = await this.port.getSignals();
        console.log("signals: ", signals);
        if(this.env.pos.config.connection_type === "usb_serial"){
            console.log("signals DSR: ", signals.dataSetReady);
            console.log("signals CTS: ", signals.clearToSend);
        }else{
            console.log("signals CTS: ", signals.clearToSend);
            console.log("signals DSR: ", signals.dataSetReady);
        }
        if(signals.clearToSend || signals.dataSetReady) {
            await new Promise(
               (res) => setTimeout(() => res(this.writer.write(comando_cod)), 20)
            );
            await this.writer.releaseLock();
            this.writer = false;
            if(this.read_Z){
                console.log("Esperando 12 seundos para leer Z o X....");
                await new Promise(
                    (res) => setTimeout(() => res(), 12000)
                );
            }
            console.log("Empezando lectura");
            while(!this.port.readable) {
                console.log("Esperando puerto");
                if (this.reader) {
                    //this.raeder.cancel();
                    await this.reader.releaseLock();
                    this.reader = false;
                }
                await new Promise(
                    (res) => setTimeout(() => res(), 50)
                );
            }
            //testeo de modal, simulando lectura

            /*await new Promise(
                    (res) => setTimeout(() => res(), 200)
             );
            return true;*/

            //fin de simulado
            await new Promise(
                    (res) => setTimeout(() => res(), 10)
             );
            if(this.reader) {
                await this.reader.releaseLock();
                this.reader = false;
            }
            if(this.port.readable) {
                this.reader = this.port.readable.getReader();
                var leer = true;
            }else{
                var leer = false;
            }

            var esperando = 0;
            while (leer) {
                try {
                    const { value, done } = await this.reader.read();
                    if (value.byteLength >= 1) {
                        console.log("Respuesta de comando: ");
                        console.log(value);
                        console.log("Respuesta detallada: ");
                        console.log(value[0]);
                        if(true){
                            if(value[0] == 6){
                                leer = false;
                                console.log("Finalizanda lectura");
                                console.log("comando aceptado");
                                await this.reader.releaseLock();
                                this.reader = false;

                                return true;
                            }else{
                                console.log("Comando no reconocido");
                                leer = false;
                                await this.reader.releaseLock();
                                this.reader = false;
                                await new Promise(
                                    (res) => setTimeout(() => res(), 100)
                                );
                                this.writer = this.port.writable.getWriter();
                                var comando_desbloqueo = ["7"];
                                var comando_desbloqueo = comando_desbloqueo.map(toBytes);
                                for(const command of comando_desbloqueo) {
                                    await new Promise(
                                        (res) => setTimeout(() => res(this.writer.write(command)), 150)
                                    );
                                }
                                await this.writer.releaseLock();
                                this.writer = false;
                                this.printing = false;
                                return true;
                            }
                        }else{
                            leer = false;
                                console.log("Finalizanda lectura");
                                console.log("comando aceptado");
                                await this.reader.releaseLock();
                                this.reader = false;

                                return true;
                        }

                    }else{
                        console.log("No hay datos");
                        //esperar 150ms
                        esperando++;
                        await new Promise(
                            (res) => setTimeout(() => res(), 200)
                        );
                    }
                    if(esperando > 20){
                                await this.reader.releaseLock();
                                this.reader = false;
                                var comando_desbloqueo = ["7"];
                                var comando_desbloqueo = comando_desbloqueo.map(toBytes);
                                this.writer = this.port.writable.getWriter();
                                for(const command of comando_desbloqueo) {
                                    await new Promise(
                                        (res) => setTimeout(() => res(this.writer.write(command)), 150)
                                    );
                                }
                                await this.writer.releaseLock();
                                this.writer = false;
                                this.printing = false;
                                return true;
                    }
                }catch(error){
                    console.log("Error al leer puerto");
                    console.error(error);
                    leer = false;
                    if (this.reader) {
                        //this.raeder.cancel();
                        this.reader.releaseLock();
                        this.reader = false;
                    }
                    var comando_desbloqueo = ["7"];
                    var comando_desbloqueo = comando_desbloqueo.map(toBytes);
                    this.writer = this.port.writable.getWriter();
                    for(const command of comando_desbloqueo) {
                                    await new Promise(
                                        (res) => setTimeout(() => res(this.writer.write(command)), 150)
                                    );
                     }
                    await this.writer.releaseLock();
                    this.writer = false;
                    this.printing = false;

                    return false;
                }
            }
        }else{
           console.log("Error signals CTS: ", signals);
           await this.writer.releaseLock();
           this.writer = false;
           this.printing = false;
           return false;
        }

    }

    async write() {
        //if(!this.writer) return;
        //this.writer = this.port.writable.getWriter();


        this.modal_imprimiendo = Swal.fire({
          title: 'Imprimiendo',
          text: 'Por favor espere.',
          imageUrl: '/pos_fiscal_printer/static/src/image/impresora.gif',
          imageWidth: 100,
          imageHeight: 100,
          imageAlt: 'Imprimiendo',
          allowOutsideClick: false,
          allowEscapeKey: false,
          allowEnterKey: false,
          showConfirmButton: false,
        });


        const TIME = this.env.pos.config.x_fiscal_commands_time || 750;
        this.printing = true;
        this.printerCommands = this.printerCommands.map(sanitize);
        console.log("Comandos: ", this.printerCommands);
        var cantidad_comandos = this.printerCommands.length;
        for(const command of this.printerCommands) {
            var is_linea = false;
            if(command.substring(0, 1) === ' ' || command.substring(0, 1) === '!' || command.substring(0, 1) === 'd' || command.substring(0, 1) === '-' ){
                is_linea = true;
            }
            if(this.printing){
                await new Promise(
                    (res) => setTimeout(() => res(this.escribe_leer(command, is_linea)), TIME)
                );
                cantidad_comandos--;
            }
        }
        this.modal_imprimiendo.close();
        if(cantidad_comandos == 0){
            console.log("Comandos finalizados");
            if(this.order){
                this.order.impresa = true;
                Swal.fire({
                  position: 'top-end',
                  icon: 'success',
                  title: 'Impresión finalizada con éxito',
                  showConfirmButton: false,
                  timer: 1500
                });
            }

        }else{
            //error en impresion
            console.log("Error en impresion, factura anulada");
            Swal.fire({
              position: 'top-end',
              icon: 'error',
              title: 'Error en impresion, factura anulada',
              showConfirmButton: false,
              timer: 2500
            });
        }

        window.clearTimeout(this.timeout);
        this.printerCommands = [];
        this.printing = false;

        this.writer = false;
        if(this.read_s2 && cantidad_comandos == 0){
            //mandar comando S2 y leer
            await this.write_s2();
        }
        if(this.read_Z){
            //mandar comando Z y leer
            const { confirmed } = await this.showPopup("ReporteZPopUp", {cancelKey: "Q", confirmKey: "Y"});
            if(confirmed){
                await this.write_Z();
            }

        }
    }

    async write_s2() {
        this.writer = this.port.writable.getWriter();
        const TIME = this.env.pos.config.x_fiscal_commands_time || 750;
        this.printerCommands = ["S1"];
        this.printerCommands = this.printerCommands.map(toBytes);
        console.log("Escribiendo S1", this.printerCommands);
        for(const command in this.printerCommands) {
            await new Promise(
                (res) => setTimeout(() => res(this.writer.write(this.printerCommands[command])), TIME)
            );
        }
        window.clearTimeout(this.timeout);
        this.printerCommands = [];
        await this.writer.releaseLock();
        this.writer = false;
        var signals_to_send = { dataTerminalReady: true };
        if(this.env.pos.config.connection_type === "usb_serial"){
            signals_to_send = { requestToSend: true };
        }
        await this.port.setSignals(signals_to_send);
        console.log("Leyendo S1", this.port.readable)
        var signals = await this.port.getSignals();
        console.log("signals: ", signals);
        if(this.env.pos.config.connection_type === "usb_serial"){
            console.log("signals DSR: ", signals.dataSetReady);
        }else{
            console.log("signals CTS: ", signals.clearToSend);
        }
        if(signals.clearToSend || signals.dataSetReady) {
            if(this.reader) {
                this.reader.releaseLock();
                this.reader = false;
            }
            if(this.port.readable) {
                this.reader = this.port.readable.getReader();
            }
            var leer = true;
            var contador = 0;
            while (this.port.readable && leer) {
                try {
                    while (leer) {
                        const { value, done } = await this.reader.read();
                        console.log(value);
                        var string = new TextDecoder().decode(value);
                        console.log(string);
                        if (string.length > 0) {
                            const myArray = string.split('\n');
                            var num_factura = myArray[2];
                            if(num_factura){
                                console.log("Numero de factura: ", num_factura);
                                this.order.num_factura = num_factura;
                                this.reader.releaseLock();
                                this.reader = false;
                                leer = false;
                                break;
                            }else{
                                contador++;
                                await new Promise(
                                       (res) => setTimeout(() => res(), 150)
                                );
                                if(contador > 10){
                                    this.reader.releaseLock();
                                    this.reader = false;
                                    leer = false;
                                    break;
                                    console.log("Error al leer numero de factura");
                                }
                            }
                        }else{
                            contador++;
                            await new Promise(
                                   (res) => setTimeout(() => res(), 150)
                            );
                            if(contador > 10){
                                this.reader.releaseLock();
                                this.reader = false;
                                leer = false;
                                break;
                                console.log("Error al leer numero de factura");
                            }
                        }
                    }
                } catch (error) {
                    leer = false;
                    console.error(error);
                } finally {
                    leer = false;
                    console.error("Finalizado");
                }
            }
            await this.rpc({
               model: 'pos.order',
               method: 'set_num_factura',
               args: [this.order.id, this.order.name, this.order.num_factura],
            });

        }

        this.printerCommands = [];
        this.read_s2 = false;
    }

    async write_Z() {
        this.writer = this.port.writable.getWriter();
        const TIME = this.env.pos.config.x_fiscal_commands_time || 750;
        this.printerCommands = ["U4z02002230200223"];
        this.printerCommands = this.printerCommands.map(toBytes);
        console.log("Escribiendo U4z02002230200223", this.printerCommands);
        for(const command in this.printerCommands) {
            await new Promise(
                (res) => setTimeout(() => res(this.writer.write(this.printerCommands[command])), TIME)
            );
        }
        window.clearTimeout(this.timeout);
        this.printerCommands = [];
        this.writer.releaseLock();
        this.writer = false;
        await new Promise(
                    (res) => setTimeout(() => res(), 12000)
        );
        console.log("Leyendo U4z02002230200223", this.port.readable)
        this.reader = false;
        if(this.port.readable) {
            this.reader = this.port.readable.getReader();
        }

        while (this.port.readable && this.read_Z) {
            try {
                while (this.read_Z) {
                    const { value, done } = await this.reader.read();
                    if (done) {
                        console.log("Done");
                        this.read_Z = false;
                        this.reader.releaseLock();
                        this.reader = false;
                        this.read_Z = false;
                        break;
                    }
                    console.log(value);
                    var string = new TextDecoder().decode(value);
                    console.log(string);
                    console.log('Desglozando U4z02002230200223');
                    const myArray = string.split('\n');
                    console.log(myArray);
                }
            } catch (error) {
                console.error(error);
                this.read_Z = false;
            }
        }

        this.printerCommands = [];
        this.read_Z = false;
    }

    async actionPrint() {
        const result = await this.setPort();
        if(!result) return;
        this.write();
    }

    async printViaUSB() {
        console.log("Detectando dispositivos via USB");
        let devices = await navigator.usb.getDevices();
        devices.forEach(device => {
            alert(device);
            if(device.productName === "Fiscal Printer"){
                console.log("Impresora Fiscal encontrada");
                this.device = device;
            }
        });
        Swal.fire({
              icon: 'error',
              title: 'Error en impresion, conexión via USB no disponible',
              showConfirmButton: true,
        });
    }

    async printZViaApi() {
        console.log("Imprimiendo Reporte Z via API");
        this.modal_imprimiendo = Swal.fire({
          title: 'Imprimiendo',
          text: 'Por favor espere.',
          imageUrl: '/pos_fiscal_printer/static/src/image/impresora.gif',
          imageWidth: 100,
          imageHeight: 100,
          imageAlt: 'Imprimiendo',
          allowOutsideClick: false,
          allowEscapeKey: false,
          allowEnterKey: false,
          showConfirmButton: false,
        });
        var url = this.env.pos.config.api_url + "/api/report_z";
        $.get(url, function(data, status){
             console.log(data);
             if (data) {
                Swal.fire({
                  position: 'top-end',
                  icon: 'success',
                  title: 'Impresión finalizada con éxito',
                  showConfirmButton: false,
                  timer: 1500
                });
             } else {
                    Swal.fire({
                          icon: 'error',
                          title: 'Error en impresion',
                          showConfirmButton: true,
                     });
             }
        });
        await new Promise(
             (res) => setTimeout(() => res(this.modal_imprimiendo.close()), 5000)
        );
    }

    async printXViaApi() {
        console.log("Imprimiendo Reporte X via API");
        this.modal_imprimiendo = Swal.fire({
          title: 'Imprimiendo',
          text: 'Por favor espere.',
          imageUrl: '/pos_fiscal_printer/static/src/image/impresora.gif',
          imageWidth: 100,
          imageHeight: 100,
          imageAlt: 'Imprimiendo',
          allowOutsideClick: false,
          allowEscapeKey: false,
          allowEnterKey: false,
          showConfirmButton: false,
        });
        var url = this.env.pos.config.api_url + "/api/report_x";
        $.get(url, function(data, status){

                console.log(data);
                if (data) {
                    Swal.fire({
                      position: 'top-end',
                      icon: 'success',
                      title: 'Impresión finalizada con éxito',
                      showConfirmButton: false,
                      timer: 1500
                    });
                } else {
                        Swal.fire({
                            icon: 'error',
                            title: 'Error en impresion',
                            showConfirmButton: true,
                        });
                }
        });
        await new Promise(
             (res) => setTimeout(() => res(this.modal_imprimiendo.close()), 5000)
        );
    }

    async printViaApi() {
        console.log("Imprimiendo via API");
        this.modal_imprimiendo = Swal.fire({
          title: 'Imprimiendo',
          text: 'Por favor espere.',
          imageUrl: '/pos_fiscal_printer/static/src/image/impresora.gif',
          imageWidth: 100,
          imageHeight: 100,
          imageAlt: 'Imprimiendo',
          allowOutsideClick: false,
          allowEscapeKey: false,
          allowEnterKey: false,
          showConfirmButton: false,
        });
        console.log(this.printerCommands.map(sanitize));
        var body = {'cmd': this.printerCommands.map(sanitize)};
        var url = this.env.pos.config.api_url + "/api/invoice";
        await ajax.jsonRpc(url, 'call', body).then((response) => {
             this.modal_imprimiendo.close();
             console.log(response);
             if (response) {
                if(response.state.lastInvoiceNumber){
                        this.order.impresa = true;
                        console.log("Finalizada con factura " + response.state.lastInvoiceNumber.toString());
                        this.order.num_factura = response.state.lastInvoiceNumber.toString();
                        this.rpc({
                           model: 'pos.order',
                           method: 'set_num_factura',
                           args: [this.order.id, this.order.name, response.state.lastInvoiceNumber.toString()],
                        });
                        Swal.fire({
                          position: 'top-end',
                          icon: 'success',
                          title: 'Impresión finalizada con éxito',
                          showConfirmButton: false,
                          timer: 1500
                        });
                }else{
                        console.log("No hay numero de factura");
                        Swal.fire({
                          position: 'top-end',
                          icon: 'success',
                          title: 'Impresión finalizada con éxito y sin número de factura',
                          showConfirmButton: false,
                          timer: 1500
                        });
                }
             }else{
                Swal.fire({
                          icon: 'error',
                          title: 'Error en impresión, ' + response.state,
                          showConfirmButton: true,
                });
             }
        }).catch((error) => {
            this.modal_imprimiendo.close();
            Swal.fire({
              icon: 'error',
              title: 'Error en impresión, ' + error.message,
              showConfirmButton: true,
            });
        });
        /*const http = new XMLHttpRequest();
        http.open('POST', this.env.pos.config.api_url + '/print_pos_ticket');
        http.setRequestHeader('Content-type', 'application/json');
        http.responseType = 'json';
        http.send(JSON.stringify({"params": {"cmd": this.printerCommands.map(sanitize)}})); // Make sure to stringify
        http.onload = function() {
            // Do whatever with response
            if (this.status == 200) {
                console.log('response', this.response); // JSON response
                if(this.response.result){
                    if(this.response.result.state.lastInvoiceNumber){
                        console.log("finalizada con factura " + this.response.result.state.lastInvoiceNumber);
                        this.order.num_factura = this.response.result.state.lastInvoiceNumber;
                        await this.rpc({
                           model: 'pos.order',
                           method: 'set_num_factura',
                           args: [this.order.id, this.order.name, this.response.result.state.lastInvoiceNumber],
                        });
                        Swal.fire({
                          position: 'top-end',
                          icon: 'success',
                          title: 'Impresión finalizada con éxito',
                          showConfirmButton: false,
                          timer: 1500
                        });
                    }else{
                        console.log("No hay numero de factura");
                        Swal.fire({
                          position: 'top-end',
                          icon: 'success',
                          title: 'Impresión finalizada con éxito y sin número de factura',
                          showConfirmButton: false,
                          timer: 1500
                        });
                    }
                }else{
                    Swal.fire({
                          icon: 'error',
                          title: 'Error en impresion, ' + this.response.state,
                          showConfirmButton: true,
                    });
                }
            } else {
                Swal.fire({
                      icon: 'error',
                      title: 'Error en impresion, conexión via API no disponible',
                      showConfirmButton: true,
                });
            }
        };
        http.onerror = function() {
            Swal.fire({
                  icon: 'error',
                  title: 'Error en impresion, conexión via API no disponible',
                  showConfirmButton: true,
            });
        };*/

    }

    async read() {
        window.clearTimeout(this.timeout);

        /*if(this.port.writable) {
            this.writer = this.port.writable.getWriter();
            this.timeout = window.setTimeout(() => this.write(), 1000);
        }*/
        console.log("Leyendo", this.port.readable)
        while (this.port.readable) {
            console.log("Leyendo");
            try {
                while (true) {
                    const { value, done } = await this.reader.read();
    
                    if (done) {
                        console.log("Done");
                        break;
                    }
    
                    (value) && console.log(value);
                }
            } catch (error) {
                console.error(error);
            } finally {
                await Promise.all([
                    this.writer?.releaseLock(),
                    this.reader.releaseLock(),
                ]);
            }
        }

        this.printerCommands = [];
        this.reader.releaseLock();
        this.reader = false;
        //await this.port.close();
    }
}