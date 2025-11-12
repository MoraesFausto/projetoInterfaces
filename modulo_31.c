#include <SPI.h>
#include "printf.h"
#include "RF24.h"

#define CE_PIN 7
#define CSN_PIN 8

#define MSG 0
#define ACK 1
#define RTS 2
#define CTS 3

#define TIMEOUT 5000 //milisegundos

RF24 radio(CE_PIN, CSN_PIN);
uint64_t address[2] = { 0x3030303030LL, 0x3030303030LL};

byte payload[5] = {0,1,2,3,4};
byte payloadRx[5] = "    ";
uint8_t origem=31;
uint8_t indice=0;


void setup() {
  Serial.begin(115200);
  while (!Serial) {
    // some boards need to wait to ensure access to serial over USB
  }

  // initialize the transceiver on the SPI bus
  if (!radio.begin()) {
    Serial.println(F("radio hardware is not responding!!"));
    while (1) {}  // hold in infinite loop
  }

  radio.setPALevel(RF24_PA_MAX);  // RF24_PA_MAX is default.
  radio.setChannel(155);
  radio.setPayloadSize(sizeof(payload));  // float datatype occupies 4 bytes
  radio.setAutoAck(false);
  radio.setCRCLength(RF24_CRC_DISABLED);
  radio.setDataRate(RF24_2MBPS);

  radio.openWritingPipe(address[0]);  // always uses pipe 0
  radio.openReadingPipe(1, address[1]);  // using pipe 1

  //For debugging info
  printf_begin();             // needed only once for printing details
  //radio.printDetails();       // (smaller) function that prints raw register values
  radio.printPrettyDetails(); // (larger) function that prints human readable data

}

void printPacote(byte *pac, int tamanho){
      Serial.print(F("Rcvd "));
      Serial.print(tamanho);  // print the size of the payload
      Serial.print(F(" O: "));
      Serial.print(pac[0]);  // print the payload's value
      Serial.print(F(" D: "));
      Serial.print(pac[1]);  // print the payload's value
      Serial.print(F(" C: "));
      Serial.print(pac[2]);  // print the payload's value
      Serial.print(F(" i: "));
      Serial.print(pac[3]);  // print the payload's value
      Serial.print(F(" : "));
      for(int i=4;i<tamanho;i++){
        Serial.print(pac[i]);
      }
      Serial.println();  // print the payload's value
}

bool aguardaMsg(int tipo){

    radio.startListening();
    unsigned long tempoInicio = millis();
    while(millis()-tempoInicio<TIMEOUT){
      if (radio.available()) { 
        uint8_t bytes = radio.getPayloadSize();  // get the size of the payload
        radio.read(&payloadRx[0], bytes);             // fetch payload from FIFO
        if(payloadRx[1]==origem && payloadRx[2]==tipo){
          radio.stopListening();
          return true;
        }
      }
      radio.flush_rx();
      delay(10);      
    }
    radio.stopListening();
    return false;
}
  

bool sendPacket(byte *pacote, int tamanho, int destino, int controle, int valor){
    pacote[0]=origem;
    pacote[1]=destino;
    pacote[2]=controle;
    pacote[3]=indice;
    if(valor != NULL){
      pacote[4]=valor;
    }
    for(int i=0;i<tamanho;i++){
      Serial.print(pacote[i]);
    }
    Serial.println();
   
    while(1){
        
       radio.startListening();
       delayMicroseconds(70);
       radio.stopListening();
       if (!radio.testCarrier()) {
          return radio.write(&pacote[0], tamanho);
          
       }else{
        Serial.println("Meio Ocupado");
        delayMicroseconds(270);
       }
       radio.flush_rx();
    }
}


void loop() {
      // Become the TX node
      int umidade = GetTemp();
      unsigned long start_timer = micros();                // start the timer
      bool report = sendPacket(&payload[0], sizeof(payload), 11, RTS, NULL);  // transmit & save the report
      report = aguardaMsg(CTS);
      if(report){
        sendPacket(&payload[0], sizeof(payload), 11, MSG, umidade);
        report = aguardaMsg(ACK);
      }
      
      unsigned long end_timer = micros();                  // end the timer
      if(report){
          Serial.println("Sucesso!");
          printPacote(payload, sizeof(payloadRx));
      }else{
          Serial.println("FALHA!");
        }


  radio.flush_rx();
  delay(10000);
}

double GetTemp(void)
{
  unsigned int wADC;
  double t;

  // The internal temperature has to be used
  // with the internal reference of 1.1V.
  // Channel 8 can not be selected with
  // the analogRead function yet.

  // Set the internal reference and mux.
  ADMUX = (_BV(REFS1) | _BV(REFS0) | _BV(MUX3));
  ADCSRA |= _BV(ADEN);  // enable the ADC

  delay(20);            // wait for voltages to become stable.

  ADCSRA |= _BV(ADSC);  // Start the ADC

  // Detect end-of-conversion
  while (bit_is_set(ADCSRA,ADSC));

  // Reading register "ADCW" takes care of how to read ADCL and ADCH.
  wADC = ADCW;

  // The offset of 324.31 could be wrong. It is just an indication.
  t = (wADC - 324.31 ) / 1.22;

  // The returned temperature is in degrees Celcius.
  return (t);
}
