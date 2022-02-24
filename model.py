from typing import Tuple

from keras import Input, Model
from keras.engine.saving import load_model
from keras.layers import LSTM, Dense, Concatenate, TimeDistributed



class VmtModel:
    """
    A class that represents the VMT model VMT-1 which makes use of visual features during sequence translation.
    This class also functions as NMT-1 when the usage of visual features is disabled in the settings.
    """

    def __init__(self, latent_dim: int, num_encoder_tokens: int = None, num_decoder_tokens: int = None,
                 filepath: str = None) -> None:
        """
        Initialise a VMT model.

        :param latent_dim: number of units in the hidden state of the LSTM
        :param num_encoder_tokens: number of tokens in the source vocabulary
        :param num_decoder_tokens: number of tokens in the target vocabulary
        :param filepath: filepath for a saved VMT model which may be loaded
        :return: None
        """
        if filepath is not None:
            model_components = self.restore_saved_model(latent_dim, filepath)
        else:
            model_components = self.define_new_model(latent_dim, num_decoder_tokens, num_encoder_tokens)

        self.entire_model, self.encoder_model, self.decoder_model = model_components

    def define_new_model(self, latent_dim: int, num_decoder_tokens: int, num_encoder_tokens: int) -> \
            Tuple[Model, Model, Model]:
        """
        Define a new VMT model and construct the encoder and decoder.

        :param latent_dim: number of units in the hidden state of the LSTM
        :param num_decoder_tokens: number of tokens in the target vocabulary
        :param num_encoder_tokens: number of tokens in the source vocabulary
        :return: tuple of model components: entire model, encoder, and decoder
        """

        print(num_encoder_tokens)
        # Adapted from https://github.com/keras-team/keras/blob/master/examples/lstm_seq2seq.py
        encoder_inputs = Input(shape=(None, num_encoder_tokens))
        print(encoder_inputs)
        encoder = LSTM(units=latent_dim, return_state=True)
        encoder_outputs, state_hidden, state_cell = encoder(encoder_inputs)

        # Discard `encoder_outputs` and only keep the states
        encoder_states = [state_hidden, state_cell]
        # Set up the decoder, using `encoder_states` as initial state.
        
        decoder_inputs = Input(shape=(None, num_decoder_tokens))
        print(num_decoder_tokens)

        # We set up our decoder to return full output sequences,
        # and to return internal states as well. We don't use the
        # return states in the training model, but we will use them in inference.
        decoder_lstm = LSTM(units=latent_dim, return_sequences=True, return_state=True)
        decoder_outputs, _, _ = decoder_lstm(decoder_inputs, initial_state=encoder_states)
        decoder_dense = Dense(num_decoder_tokens, activation='softmax')
        decoder_outputs = decoder_dense(decoder_outputs)
        

        
        entire_model = Model([encoder_inputs, decoder_inputs], decoder_outputs)
    
        # Define a sampling model
        encoder_model = Model(encoder_inputs, encoder_states)
        decoder_state_input_hidden = Input(shape=(latent_dim,))
        decoder_state_input_cell = Input(shape=(latent_dim,))
        decoder_states_inputs = [decoder_state_input_hidden, decoder_state_input_cell]
        decoder_outputs, state_hidden, state_cell = decoder_lstm(
            decoder_inputs, initial_state=decoder_states_inputs)
        decoder_states = [state_hidden, state_cell]
        decoder_outputs = decoder_dense(decoder_outputs)
        decoder_model = Model(
            [decoder_inputs] + decoder_states_inputs,
            [decoder_outputs] + decoder_states)

        return entire_model, encoder_model, decoder_model

    @staticmethod
    def restore_saved_model(latent_dim: int, filepath: str) -> Tuple[Model, Model, Model]:
        """
        Restore a saved VMT model and construct the encoder and decoder.

        :param latent_dim: number of units in the hidden state of the saved LSTM
        :param filepath: filepath of model to be restored
        :return: tuple of model components: entire model, encoder, and decoder
        """

        # Adapted from https://github.com/keras-team/keras/blob/master/examples/lstm_seq2seq_restore.py
        entire_model = load_model(filepath)

        encoder_inputs = entire_model.input[0]  # input_1
        print(encoder_inputs)
        encoder_outputs, state_h_enc, state_c_enc = entire_model.layers[2].output  # lstm_1
        encoder_states = [state_h_enc, state_c_enc]
        encoder_model = Model(encoder_inputs, encoder_states)
        
        print("11111111111111")
        decoder_inputs = entire_model.input[1]  # input_2
        print("decoder inputs", decoder_inputs)
        decoder_state_input_h = Input(shape=(latent_dim,), name='input_3')
        decoder_state_input_c = Input(shape=(latent_dim,), name='input_4')
        decoder_states_inputs = [decoder_state_input_h, decoder_state_input_c]
        decoder_lstm = entire_model.layers[3]
        decoder_outputs, state_h_dec, state_c_dec = decoder_lstm(
            decoder_inputs, initial_state=decoder_states_inputs)
        decoder_states = [state_h_dec, state_c_dec]
        decoder_dense = entire_model.layers[4]
        decoder_outputs = decoder_dense(decoder_outputs)
        decoder_model = Model(
            [decoder_inputs] + decoder_states_inputs,
            [decoder_outputs] + decoder_states)

        return entire_model, encoder_model, decoder_model

    def get_entire_model(self) -> Model:
        """
        Get the entire VMT model.

        :return: entire VMT model
        """
        return self.entire_model

    def get_sampling_encoder(self) -> Model:
        """
        Get the sampling encoder of the VMT model.

        :return: sampling encoder of VMT model
        """
        return self.encoder_model

    def get_sampling_decoder(self) -> Model:
        """
        Get the sampling decoder of the VMT model.

        :return: sampling decoder of VMT model
        """
        return self.decoder_model
